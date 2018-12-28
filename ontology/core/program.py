#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import binascii
from typing import List

from ontology.core.program_info import ProgramInfo
from ontology.crypto.key_type import KeyType
from ontology.exception.error_code import ErrorCode
from ontology.exception.exception import SDKException
from ontology.io.binary_reader import BinaryReader
from ontology.vm.op_code import PUSHBYTES75, PUSHBYTES1, PUSHDATA1, PUSHDATA2, PUSHDATA4, CHECKSIG, CHECKMULTISIG, PUSH1
from ontology.io.binary_writer import BinaryWriter
from ontology.io.memory_stream import StreamManager
from ontology.utils.utils import bytes_reader
from ontology.vm.params_builder import ParamsBuilder
from ecdsa import util
from ontology.common import define


class ProgramBuilder(object):

    @staticmethod
    def program_from_params(sigs):
        code = bytearray()
        for sig in sigs:
            code += ProgramBuilder.push_bytes(sig)
        return code

    @staticmethod
    def program_from_pubkey(public_key):
        builder = ParamsBuilder()
        builder.emit_push_byte_array(public_key)
        builder.emit(CHECKSIG)
        return builder.to_bytes()

    @staticmethod
    def push_bytes(data):
        ms = StreamManager.GetStream()
        writer = BinaryWriter(ms)
        if len(data) == 0:
            raise ValueError("push data error: data is null")
        if len(data) <= int.from_bytes(PUSHBYTES75, 'little') + 1 - int.from_bytes(PUSHBYTES1, 'little'):
            num = len(data) + int.from_bytes(PUSHBYTES1, 'little') - 1
            writer.write_byte(num)
        elif len(data) < 0x100:
            writer.write_byte(PUSHDATA1)
            writer.write_uint8(len(data))
        elif len(data) < 0x10000:
            writer.write_byte(PUSHDATA2)
            writer.write_uint16(len(data))
        else:
            writer.write_byte(PUSHDATA4)
            writer.write_uint32(len(data))
        writer.write_bytes(data)
        ms.flush()
        res = ms.ToArray()
        StreamManager.ReleaseStream(ms)
        res = bytes_reader(res)
        return res

    @staticmethod
    def read_bytes(reader: BinaryReader):
        code = reader.read_byte()
        if code == int.from_bytes(PUSHDATA4, 'little'):
            temp = reader.read_uint32()
            key_len = temp
        elif code == int.from_bytes(PUSHDATA2, 'little'):
            temp = reader.read_uint16()
            key_len = int(temp)
        elif code == int.from_bytes(PUSHDATA1, 'little'):
            temp = reader.read_uint8()
            key_len = int(temp)
        elif int.from_bytes(PUSHBYTES75, 'little') >= code >= int.from_bytes(PUSHBYTES1, 'little'):
            key_len = code - int.from_bytes(PUSHBYTES1, 'little') + 1
        else:
            key_len = 0
        res = reader.read_bytes(key_len)
        return res

    @staticmethod
    def compare_pubkey(pub_key: bytes):
        if not isinstance(pub_key, bytes):
            raise SDKException(ErrorCode.other_error('Invalid key.'))
        if KeyType.from_pubkey(pub_key) == KeyType.SM2:
            raise SDKException(ErrorCode.other_error('Unsupported key type'))
        elif KeyType.from_pubkey(pub_key) == KeyType.ECDSA:
            x = pub_key[1:]
            return util.string_to_number(x)
        else:
            return str(pub_key)

    @staticmethod
    def sort_public_keys(pub_keys: List[bytes] or List[str]):
        """
        :param pub_keys: a list of public keys in format of bytes.
        :return: sorted public keys.
        """
        for index, key in range(len(pub_keys)):
            if isinstance(key, str):
                pub_keys[index] = binascii.a2b_hex(key)
        return sorted(pub_keys, key=ProgramBuilder.compare_pubkey)

    @staticmethod
    def program_from_multi_pubkey(m: int, pub_keys: []) -> bytes:
        n = len(pub_keys)
        if m <= 0:
            raise SDKException(ErrorCode.other_error(f'Param error: m == {m}'))
        if m > n:
            raise SDKException(ErrorCode.other_error(f'Param error: m == {m} n == {n}'))
        if n > define.MULTI_SIG_MAX_PUBKEY_SIZE:
            raise SDKException(ErrorCode.other_error(f'Param error: n == {n} > {define.MULTI_SIG_MAX_PUBKEY_SIZE}'))
        builder = ParamsBuilder()
        builder.emit_push_integer(m)
        pub_keys = ProgramBuilder.sort_public_keys(pub_keys)
        for pk in pub_keys:
            builder.emit_push_byte_array(pk)
        builder.emit_push_integer(n)
        builder.emit(CHECKMULTISIG)
        return builder.to_bytes()

    @staticmethod
    def get_param_info(program: bytes):
        ms = StreamManager.GetStream(program)
        reader = BinaryReader(ms)
        param_info = []
        while True:
            try:
                res = ProgramBuilder.read_bytes(reader)
            except SDKException:
                break
            param_info.append(res)
        return param_info

    @staticmethod
    def get_program_info(program: bytes) -> ProgramInfo:
        length = len(program)
        end = program[length - 1]
        temp = program[:length - 1]
        ms = StreamManager.GetStream(temp)
        reader = BinaryReader(ms)
        info = ProgramInfo()
        if end == int.from_bytes(CHECKSIG, 'little'):
            pub_keys = ProgramBuilder.read_bytes(reader)
            info.set_pubkey([pub_keys])
            info.set_m(1)
        elif end == int.from_bytes(CHECKMULTISIG, 'little'):
            length = program[len(program) - 2] - int.from_bytes(PUSH1, 'little') + 1
            m = reader.read_byte() - int.from_bytes(PUSH1, 'little') + 1
            pub = []
            for i in range(length):
                pub.append(reader.read_var_bytes())
            info.set_pubkey(pub)
            info.set_m(m)
        return info
