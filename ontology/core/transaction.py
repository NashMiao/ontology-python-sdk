#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import binascii

from typing import List
from enum import Enum

from ontology.core.sig import Sig
from ontology.common import define
from ontology.crypto.digest import Digest
from ontology.common.address import Address
from ontology.account.account import Account
from ontology.core.program import ProgramBuilder
from ontology.io.binary_writer import BinaryWriter
from ontology.io.binary_reader import BinaryReader
from ontology.io.memory_stream import StreamManager
from ontology.exception.error_code import ErrorCode
from ontology.exception.exception import SDKException


class TransactionType(Enum):
    Bookkeeping = 0x00
    Bookkeeper = 0x02
    Claim = 0x03
    Enrollment = 0x04
    Vote = 0x05
    DeployCode = 0xd0
    InvokeCode = 0xd1
    TransferTransaction = 0x80


class Transaction(object):
    def __init__(self, version=0, tx_type=None, nonce=None, gas_price=None, gas_limit=None, payer=None, payload=None,
                 attributes=None, sig_list: List[Sig] = None):
        self.version = version
        self.tx_type = tx_type
        self.nonce = nonce
        self.gas_price = gas_price
        self.gas_limit = gas_limit
        if payer is None or payer == b'' or payer == bytearray():
            payer = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        self.payer = payer
        self.payload = payload
        self.attributes = attributes
        self.sig_list = sig_list

    def __iter__(self):
        data = dict()
        data['version'] = self.version
        data['txType'] = self.tx_type
        data['nonce'] = self.nonce
        data['gasPrice'] = self.gas_price
        data['gasLimit'] = self.gas_limit
        data['payer'] = Address(self.payer).b58encode()
        data['payload'] = binascii.b2a_hex(self.payload).decode('ascii')
        data['attributes'] = binascii.b2a_hex(self.attributes).decode('ascii')
        data['sigs'] = list()
        for sig in self.sig_list:
            data['sigs'].append(dict(sig))
        for key, value in data.items():
            yield (key, value)

    def serialize_unsigned(self, is_str: bool = False) -> bytes or str:
        ms = StreamManager.get_stream()
        writer = BinaryWriter(ms)
        writer.write_uint8(self.version)
        writer.write_uint8(self.tx_type)
        writer.write_uint32(self.nonce)
        writer.write_uint64(self.gas_price)
        writer.write_uint64(self.gas_limit)
        writer.write_bytes(self.payer)
        self.serialize_exclusive_data(writer)
        if self.payload is not None:
            writer.write_var_bytes(bytes(self.payload))
        writer.write_var_int(len(self.attributes))
        ms.flush()
        hex_bytes = ms.hexlify()
        StreamManager.release_stream(ms)
        if is_str:
            return binascii.a2b_hex(hex_bytes)
        else:
            return hex_bytes

    def serialize_exclusive_data(self, writer):
        pass

    def hash256_explorer(self) -> str:
        tx_serial = self.serialize_unsigned(is_str=True)
        digest = Digest.hash256(tx_serial)
        if not isinstance(digest, bytes):
            raise SDKException(ErrorCode.require_bytes_params)
        return binascii.b2a_hex(digest[::-1]).decode('ascii')

    def hash256_bytes(self) -> bytes:
        tx_serial = self.serialize_unsigned()
        tx_serial = binascii.a2b_hex(tx_serial)
        digest = Digest.hash256(tx_serial, False)
        if not isinstance(digest, bytes):
            raise SDKException(ErrorCode.require_bytes_params)
        return digest

    def hash256_hex(self) -> str:
        tx_serial = self.serialize_unsigned(is_str=True)
        digest = Digest.hash256(tx_serial, is_hex=True)
        if not isinstance(digest, str):
            raise SDKException(ErrorCode.require_str_params)
        return digest

    def serialize(self, is_hex: bool = False) -> bytes:
        ms = StreamManager.get_stream()
        writer = BinaryWriter(ms)
        writer.write_bytes(self.serialize_unsigned())
        writer.write_var_int(len(self.sig_list))
        for sig in self.sig_list:
            writer.write_bytes(sig.serialize())
        ms.flush()
        bytes_tx = ms.hexlify()
        StreamManager.release_stream(ms)
        if is_hex:
            return bytes_tx
        else:
            return binascii.a2b_hex(bytes_tx)

    @staticmethod
    def deserialize_from(bytes_tx: bytes):
        ms = StreamManager.get_stream(bytes_tx)
        reader = BinaryReader(ms)
        tx = Transaction()
        tx.version = reader.read_uint8()
        tx.tx_type = reader.read_uint8()
        tx.nonce = reader.read_uint32()
        tx.gas_price = reader.read_uint64()
        tx.gas_limit = reader.read_uint64()
        tx.payer = reader.read_bytes(20)
        tx.payload = reader.read_var_bytes()
        attribute_len = reader.read_var_int()
        if attribute_len is 0:
            tx.attributes = bytearray()
        sig_len = reader.read_var_int()
        tx.sig_list = list()
        for _ in range(0, sig_len):
            tx.sig_list.append(Sig.deserialize(reader))
        return tx

    def sign_transaction(self, signer: Account):
        """
        This interface is used to sign the transaction.

        :param signer: an Account object which will sign the transaction.
        :return: a Transaction object which has been signed.
        """
        tx_hash = self.hash256_bytes()
        sig_data = signer.generate_signature(tx_hash)
        sig = [Sig([signer.get_public_key_bytes()], 1, [sig_data])]
        self.sig_list = sig

    def add_sign_transaction(self, signer: Account):
        """
        This interface is used to add signature into the transaction.

        :param signer: an Account object which will sign the transaction.
        :return: a Transaction object which has been signed.
        """
        if self.sig_list is None or len(self.sig_list) == 0:
            self.sig_list = []
        elif len(self.sig_list) >= define.TX_MAX_SIG_SIZE:
            raise SDKException(ErrorCode.param_err('the number of transaction signatures should not be over 16'))
        tx_hash = self.hash256_bytes()
        sig_data = signer.generate_signature(tx_hash)
        sig = Sig([signer.get_public_key_bytes()], 1, [sig_data])
        self.sig_list.append(sig)

    def add_multi_sign_transaction(self, m: int, pub_keys: List[bytes] or List[str], signer: Account):
        """
        This interface is used to generate an Transaction object which has multi signature.

        :param tx: a Transaction object which will be signed.
        :param m: the amount of signer.
        :param pub_keys: a list of public keys.
        :param signer: an Account object which will sign the transaction.
        :return: a Transaction object which has been signed.
        """
        for index, pk in enumerate(pub_keys):
            if isinstance(pk, str):
                pub_keys[index] = pk.encode('ascii')
        pub_keys = ProgramBuilder.sort_public_keys(pub_keys)
        tx_hash = self.hash256_bytes()
        sig_data = signer.generate_signature(tx_hash)
        if self.sig_list is None or len(self.sig_list) == 0:
            self.sig_list = []
        elif len(self.sig_list) >= define.TX_MAX_SIG_SIZE:
            raise SDKException(ErrorCode.param_err('the number of transaction signatures should not be over 16'))
        else:
            for i in range(len(self.sig_list)):
                if self.sig_list[i].public_keys == pub_keys:
                    if len(self.sig_list[i].sig_data) + 1 > len(pub_keys):
                        raise SDKException(ErrorCode.param_err('too more sigData'))
                    if self.sig_list[i].m != m:
                        raise SDKException(ErrorCode.param_err('M error'))
                    self.sig_list[i].sig_data.append(sig_data)
                    return
        sig = Sig(pub_keys, m, [sig_data])
        self.sig_list.append(sig)
