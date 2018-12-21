#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import unittest
import binascii

from random import choice

from ontology.ont_sdk import OntologySdk
from ontology.account.account import Account
from ontology.crypto.signature_scheme import SignatureScheme
from ontology.network.connect_manager import TEST_RPC_ADDRESS
from ontology.utils.contract_data_parser import ContractDataParser
from ontology.utils.contract_event_parser import ContractEventParser
from ontology.smart_contract.neo_contract.invoke_function import InvokeFunction

sdk = OntologySdk()
remote_rpc_address = choice(TEST_RPC_ADDRESS)
local_rpc_address = 'http://localhost:20336'
sdk.rpc.set_address(remote_rpc_address)
gas_limit = 20000000
gas_price = 500

private_key1 = '523c5fcf74823831756f0bcb3634234f10b3beb1c05595058534577752ad2d9f'
private_key2 = '75de8489fcb2dcaf2ef3cd607feffde18789de7da129b5e97c81e001793cb7cf'
private_key3 = '1383ed1fe570b6673351f1a30a66b21204918ef8f673e864769fa2a653401114'

acct1 = Account(private_key1, SignatureScheme.SHA256withECDSA)
acct2 = Account(private_key2, SignatureScheme.SHA256withECDSA)
acct3 = Account(private_key3, SignatureScheme.SHA256withECDSA)


class TestWalletManager(unittest.TestCase):
    def test_oep4_name(self):
        contract_address = '1ddbb682743e9d9e2b71ff419e97a9358c5c4ee9'
        bytearray_contract_address = bytearray(binascii.a2b_hex(contract_address))
        bytearray_contract_address.reverse()
        func = InvokeFunction('name')
        result = sdk.neo_vm().send_transaction(bytearray_contract_address, None, None, 0, 0, func, True)
        name = result['Result']
        name = ContractDataParser.to_utf8_str(name)
        self.assertEqual('DXToken', name)

    def test_oep4_symbol(self):
        hex_contract_address = '1ddbb682743e9d9e2b71ff419e97a9358c5c4ee9'
        func = InvokeFunction('symbol')
        result = sdk.neo_vm().send_transaction(hex_contract_address, None, None, 0, 0, func, True)
        symbol = result['Result']
        symbol = ContractDataParser.to_utf8_str(symbol)
        self.assertEqual('DX', symbol)

    def test_oep4_decimal(self):
        hex_contract_address = '1ddbb682743e9d9e2b71ff419e97a9358c5c4ee9'
        func = InvokeFunction('decimals')
        result = sdk.neo_vm().send_transaction(hex_contract_address, None, None, 0, 0, func, True)
        decimals = result['Result']
        decimals = ContractDataParser.to_int(decimals)
        self.assertEqual(10, decimals)

    def test_oep4_total_supply(self):
        hex_contract_address = '1ddbb682743e9d9e2b71ff419e97a9358c5c4ee9'
        func = InvokeFunction('totalSupply')
        result = sdk.neo_vm().send_transaction(hex_contract_address, None, None, 0, 0, func, True)
        total_supply = result['Result']
        total_supply = ContractDataParser.to_int(total_supply)
        self.assertEqual(10000000000000000000, total_supply)

    def test_oep4_balance_of(self):
        hex_contract_address = '1ddbb682743e9d9e2b71ff419e97a9358c5c4ee9'
        func = InvokeFunction('balanceOf')
        bytes_address = acct1.get_address().to_bytes()
        func.set_params_value(bytes_address)
        result = sdk.neo_vm().send_transaction(hex_contract_address, None, None, 0, 0, func, True)
        balance = result['Result']
        balance = ContractDataParser.to_int(balance)
        self.assertGreater(balance, 100)

    def test_oep4_transfer(self):
        hex_contract_address = '1ddbb682743e9d9e2b71ff419e97a9358c5c4ee9'
        func = InvokeFunction('transfer')
        bytes_from_address = acct1.get_address().to_bytes()
        bytes_to_address = acct2.get_address().to_bytes()
        value = 1
        func.set_params_value(bytes_from_address, bytes_to_address, value)
        tx_hash = sdk.neo_vm().send_transaction(hex_contract_address, acct1, acct2, gas_limit, gas_price, func, False)
        self.assertEqual(64, len(tx_hash))
        time.sleep(6)
        event = sdk.rpc.get_smart_contract_event_by_tx_hash(tx_hash)
        states = ContractEventParser.get_states_by_contract_address(event, hex_contract_address)
        states[0] = ContractDataParser.to_utf8_str(states[0])
        self.assertEqual('transfer', states[0])
        states[1] = ContractDataParser.to_b58_address(states[1])
        self.assertEqual(acct1.get_address().b58encode(), states[1])
        states[2] = ContractDataParser.to_b58_address(states[2])
        self.assertEqual(acct2.get_address().b58encode(), states[2])
        states[3] = ContractDataParser.to_int(states[3])
        self.assertEqual(value, states[3])

    def test_oep4_approve(self):
        hex_contract_address = '1ddbb682743e9d9e2b71ff419e97a9358c5c4ee9'
        func = InvokeFunction('approve')
        bytes_owner_address = acct1.get_address().to_bytes()
        bytes_spender_address = acct2.get_address().to_bytes()
        amount = 10
        func.set_params_value(bytes_owner_address, bytes_spender_address, amount)
        tx_hash = sdk.neo_vm().send_transaction(hex_contract_address, acct1, acct2, gas_limit, gas_price, func, False)
        self.assertEqual(64, len(tx_hash))
        time.sleep(6)
        event = sdk.rpc.get_smart_contract_event_by_tx_hash(tx_hash)
        states = ContractEventParser.get_states_by_contract_address(event, hex_contract_address)
        states[0] = ContractDataParser.to_utf8_str(states[0])
        self.assertEqual('approval', states[0])
        states[1] = ContractDataParser.to_b58_address(states[1])
        self.assertEqual(acct1.get_address_base58(), states[1])
        states[2] = ContractDataParser.to_b58_address(states[2])
        self.assertEqual(acct2.get_address_base58(), states[2])
        states[3] = ContractDataParser.to_int(states[3])
        self.assertEqual(amount, states[3])

    def test_oep4_transfer_multi(self):
        hex_contract_address = '1ddbb682743e9d9e2b71ff419e97a9358c5c4ee9'
        bytes_from_address1 = acct1.get_address().to_bytes()
        bytes_to_address1 = acct2.get_address().to_bytes()
        value1 = 2
        transfer1 = [bytes_from_address1, bytes_to_address1, value1]
        bytes_from_address2 = acct2.get_address().to_bytes()
        bytes_to_address2 = acct3.get_address().to_bytes()
        value2 = 1
        transfer2 = [bytes_from_address2, bytes_to_address2, value2]
        func = InvokeFunction('transferMulti')
        func.set_params_value(transfer1, transfer2)
        tx_hash = sdk.neo_vm().send_transaction(hex_contract_address, acct1, acct2, gas_limit, gas_price, func, False)
        time.sleep(6)
        event = sdk.rpc.get_smart_contract_event_by_tx_hash(tx_hash)
        states_list = ContractEventParser.get_states_by_contract_address(event, hex_contract_address)
        states_list[0][0] = ContractDataParser.to_utf8_str(states_list[0][0])
        self.assertEqual('transfer', states_list[0][0])
        states_list[0][1] = ContractDataParser.to_b58_address(states_list[0][1])
        self.assertEqual(acct1.get_address().b58encode(), states_list[0][1])
        states_list[0][2] = ContractDataParser.to_b58_address(states_list[0][2])
        self.assertEqual(acct2.get_address().b58encode(), states_list[0][2])
        states_list[0][3] = ContractDataParser.to_int(states_list[0][3])
        self.assertEqual(value1, states_list[0][3])

        states_list[1][0] = ContractDataParser.to_utf8_str(states_list[1][0])
        self.assertEqual('transfer', states_list[1][0])
        states_list[1][1] = ContractDataParser.to_b58_address(states_list[1][1])
        self.assertEqual(acct2.get_address().b58encode(), states_list[1][1])
        states_list[1][2] = ContractDataParser.to_b58_address(states_list[1][2])
        self.assertEqual(acct3.get_address().b58encode(), states_list[1][2])
        states_list[1][3] = ContractDataParser.to_int(states_list[1][3])
        self.assertEqual(value2, states_list[1][3])

    def test_transfer_multi_args_0(self):
        transfer_1 = [acct1.get_address().to_bytes(), acct2.get_address().to_bytes(), 10]
        transfer_2 = [acct2.get_address().to_bytes(), acct3.get_address().to_bytes(), 100]
        transfer_list = [transfer_1, transfer_2]
        hex_contract_address = 'ca91a73433c016fbcbcf98051d385785a6a5d9be'
        func = InvokeFunction('transfer_multi')
        func.set_params_value(transfer_list)
        tx_hash = sdk.neo_vm().send_transaction(hex_contract_address, acct1, acct2, gas_limit, gas_price, func, False)
        self.assertEqual(64, len(tx_hash))
        time.sleep(6)
        event = sdk.rpc.get_smart_contract_event_by_tx_hash(tx_hash)
        states = ContractEventParser.get_states_by_contract_address(event, hex_contract_address)
        states[0] = ContractDataParser.to_utf8_str(states[0])
        states[1][0][0] = ContractDataParser.to_b58_address(states[1][0][0])
        self.assertEqual(acct1.get_address_base58(), states[1][0][0])
        states[1][0][1] = ContractDataParser.to_b58_address(states[1][0][1])
        self.assertEqual(acct2.get_address_base58(), states[1][0][1])
        states[1][0][2] = ContractDataParser.to_int(states[1][0][2])
        self.assertEqual(10, states[1][0][2])
        states[1][1][0] = ContractDataParser.to_b58_address(states[1][1][0])
        self.assertEqual(acct2.get_address_base58(), states[1][1][0])
        states[1][1][1] = ContractDataParser.to_b58_address(states[1][1][1])
        self.assertEqual(acct3.get_address_base58(), states[1][1][1])
        states[1][1][2] = ContractDataParser.to_int(states[1][1][2])
        self.assertEqual(100, states[1][1][2])

    def test_transfer_multi_args(self):
        transfer_1 = [acct1.get_address().to_bytes(), acct2.get_address().to_bytes(), 10]
        transfer_2 = [acct2.get_address().to_bytes(), acct3.get_address().to_bytes(), 100]
        hex_contract_address = 'ca91a73433c016fbcbcf98051d385785a6a5d9be'
        func = InvokeFunction('transfer_multi_args')
        func.set_params_value(transfer_1, transfer_2)
        tx_hash = sdk.neo_vm().send_transaction(hex_contract_address, acct1, acct2, gas_limit, gas_price, func, False)
        self.assertEqual(64, len(tx_hash))
        time.sleep(6)
        event = sdk.rpc.get_smart_contract_event_by_tx_hash(tx_hash)
        states = ContractEventParser.get_states_by_contract_address(event, hex_contract_address)
        states[0] = ContractDataParser.to_utf8_str(states[0])
        self.assertEqual('transfer_multi_args', states[0])
        states[1][0][0] = ContractDataParser.to_b58_address(states[1][0][0])
        self.assertEqual(acct1.get_address_base58(), states[1][0][0])
        states[1][0][1] = ContractDataParser.to_b58_address(states[1][0][1])
        self.assertEqual(acct2.get_address_base58(), states[1][0][1])
        states[1][0][2] = ContractDataParser.to_int(states[1][0][2])
        self.assertEqual(10, states[1][0][2])
        states[1][1][0] = ContractDataParser.to_b58_address(states[1][1][0])
        self.assertEqual(acct2.get_address_base58(), states[1][1][0])
        states[1][1][1] = ContractDataParser.to_b58_address(states[1][1][1])
        self.assertEqual(acct3.get_address_base58(), states[1][1][1])
        states[1][1][2] = ContractDataParser.to_int(states[1][1][2])
        self.assertEqual(100, states[1][1][2])

    def test_notify_pre_exec(self):
        bool_msg = True
        int_msg = 1024
        list_msg = [1, 1024, 2048]
        str_msg = 'Hello'
        bytes_address_msg = acct1.get_address().to_bytes()
        hex_contract_address = '4855735ffadad50e7000d73e1c4e96f38d225f70'
        notify_args = InvokeFunction('notify_args')
        notify_args.set_params_value(bool_msg, int_msg, list_msg, str_msg, bytes_address_msg)
        rpc_address = 'http://polaris5.ont.io:20336'
        sdk.set_rpc_address(rpc_address)
        response = sdk.neo_vm().send_transaction(hex_contract_address, None, None, 0, 0, notify_args, True)
        sdk.set_rpc_address(remote_rpc_address)
        response['Result'] = ContractDataParser.to_bool(response['Result'])
        self.assertEqual(1, response['State'])
        self.assertEqual(20000, response['Gas'])
        self.assertEqual(True, response['Result'])
        notify = response['Notify'][0]
        self.assertEqual(hex_contract_address, notify['ContractAddress'])
        states = notify['States']
        states[0] = ContractDataParser.to_utf8_str(states[0])
        self.assertEqual('notify args', states[0])
        states[1] = ContractDataParser.to_bool(states[1])
        self.assertEqual(True, states[1])
        states[2] = ContractDataParser.to_int(states[2])
        self.assertEqual(int_msg, states[2])
        states[3] = ContractDataParser.to_int_list(states[3])
        self.assertEqual(list_msg, states[3])
        states[4] = ContractDataParser.to_utf8_str(states[4])
        self.assertEqual(str_msg, states[4])
        states[5] = ContractDataParser.to_b58_address(states[5])
        self.assertEqual(acct1.get_address_base58(), states[5])

    def test_notify(self):
        hex_contract_address = '6690b6638251be951dded8c537678200a470c679'
        notify_args = InvokeFunction('testHello')
        bool_msg = True
        int_msg = 1
        bytes_msg = b'Hello'
        str_msg = 'Hello'
        bytes_address_msg = acct1.get_address().to_bytes()
        notify_args.set_params_value(bool_msg, int_msg, bytes_msg, str_msg, bytes_address_msg)
        tx_hash = sdk.neo_vm().send_transaction(hex_contract_address, None, acct1, gas_limit, gas_price, notify_args,
                                                False)
        time.sleep(6)
        event = sdk.rpc.get_smart_contract_event_by_tx_hash(tx_hash)
        states = ContractEventParser.get_states_by_contract_address(event, hex_contract_address)
        states[0] = ContractDataParser.to_utf8_str(states[0])
        self.assertEqual('testHello', states[0])
        states[1] = ContractDataParser.to_bool(states[1])
        self.assertEqual(bool_msg, states[1])
        states[2] = ContractDataParser.to_int(states[2])
        self.assertEqual(int_msg, states[2])
        states[3] = ContractDataParser.to_bytes(states[3])
        self.assertEqual(bytes_msg, states[3])
        states[4] = ContractDataParser.to_utf8_str(states[4])
        self.assertEqual(str_msg, states[4])
        states[5] = ContractDataParser.to_b58_address(states[5])
        self.assertEqual(acct1.get_address_base58(), states[5])

    def test_list(self):
        hex_contract_address = '6690b6638251be951dded8c537678200a470c679'
        list_msg = [1, 10, 1024, [1, 10, 1024, [1, 10, 1024]]]
        func = InvokeFunction('testList')
        func.set_params_value(list_msg)
        tx_hash = sdk.neo_vm().send_transaction(hex_contract_address, None, acct1, gas_limit, gas_price, func, False)
        time.sleep(6)
        event = sdk.rpc.get_smart_contract_event_by_tx_hash(tx_hash)
        states = ContractEventParser.get_states_by_contract_address(event, hex_contract_address)
        states[0] = ContractDataParser.to_utf8_str(states[0])
        self.assertEqual('testMsgList', states[0])
        states[1] = ContractDataParser.to_int_list(states[1])
        self.assertEqual(list_msg, states[1])

    def test_dict(self):
        hex_contract_address = '6690b6638251be951dded8c537678200a470c679'
        dict_msg = {'key': 'value'}
        func = InvokeFunction('testMap')
        func.set_params_value(dict_msg)
        result = sdk.neo_vm().send_transaction(hex_contract_address, None, None, 0, 0, func, True)
        dict_value = result['Result']
        dict_value = ContractDataParser.to_utf8_str(dict_value)
        self.assertEqual('value', dict_value)
        list_value = [1, 10, 1024, [1, 10, 1024, [1, 10, 1024]]]
        dict_msg = {'key': list_value}
        func = InvokeFunction('testMap')
        func.set_params_value(dict_msg)
        result = sdk.neo_vm().send_transaction(hex_contract_address, None, None, 0, 0, func, True)
        dict_value = result['Result']
        dict_value = ContractDataParser.to_int_list(dict_value)
        self.assertEqual(list_value, dict_value)

    def test_get_dict(self):
        hex_contract_address = '6690b6638251be951dded8c537678200a470c679'
        key = 'key'
        func = InvokeFunction('testGetMap')
        func.set_params_value(key)
        result = sdk.neo_vm().send_transaction(hex_contract_address, None, None, 0, 0, func, True)
        dict_value = result['Result']
        dict_value = ContractDataParser.to_utf8_str(dict_value)
        self.assertEqual('value', dict_value)

    def test_dict_in_ctx(self):
        hex_contract_address = '6690b6638251be951dded8c537678200a470c679'
        bool_value = True
        int_value = 100
        str_value = 'value3'
        dict_value = {'key': 'value'}
        list_value = [1, 10, 1024, [1, 10, 1024, [1, 10, 1024]]]
        dict_msg = {'key': dict_value, 'key1': int_value, 'key2': str_value, 'key3': bool_value, 'key4': list_value}
        func = InvokeFunction('testMapInMap')
        func.set_params_value(dict_msg)
        tx_hash = sdk.neo_vm().send_transaction(hex_contract_address, None, acct1, gas_limit, gas_price, func, False)
        time.sleep(6)
        event = sdk.rpc.get_smart_contract_event_by_tx_hash(tx_hash)
        states = ContractEventParser.get_states_by_contract_address(event, hex_contract_address)
        states[0] = ContractDataParser.to_utf8_str(states[0])
        self.assertEqual('mapInfo', states[0])
        states[1] = ContractDataParser.to_dict(states[1])
        self.assertTrue(isinstance(states[1], dict))

    def test_get_dict_in_ctx(self):
        hex_contract_address = '6690b6638251be951dded8c537678200a470c679'
        key = 'key'
        func = InvokeFunction('testGetMapInMap')
        func.set_params_value(key)
        result = sdk.neo_vm().send_transaction(hex_contract_address, None, None, 0, 0, func, True)
        value = result['Result']
        value = ContractDataParser.to_utf8_str(value)
        self.assertEqual('value', value)


if __name__ == '__main__':
    unittest.main()
