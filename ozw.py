# Copyright (c) 2015-2016 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import binascii
import logging
import os
import signal
import sys
from functools import partial
from pprint import pprint as pp, pformat as pf

from louie import dispatcher, All
from openzwave.controller import ZWaveController
from openzwave.network import ZWaveNetwork
from openzwave.option import ZWaveOption

from isac import IsacNode, IsacValue
from isac.tools import green, Queue


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

logger.info('Starting')


class AlidronOZW(object):

    def __init__(self, device, isac_node):
        self.isac_node = isac_node

        self.signals = {}

        self._ozw_notif_queue = Queue()
        self._running = True
        green.spawn(self._notif_reader)

        self.options = ZWaveOption(
            device,
            config_path='/usr/share/openzwave/config',
            user_path='./user-dir',
            cmd_line=''
        )
        self.options.set_log_file("./user-dir/OZW_Log.log")
        self.options.set_append_log_file(False)
        self.options.set_console_output(False)
        self.options.set_save_log_level('Info')
        self.options.set_logging(False)
        self.options.lock()

        self.network = ZWaveNetwork(self.options, log=None)

        notif_to_func = [
            (ZWaveNetwork.SIGNAL_NETWORK_STARTED,    self.notif_network_started),
            (ZWaveNetwork.SIGNAL_NETWORK_RESETTED,   self.notif_network_resetted),
            (ZWaveNetwork.SIGNAL_NETWORK_READY,      self.notif_network_ready),
            (ZWaveNetwork.SIGNAL_NODE_ADDED,         self.notif_node_added),
            (ZWaveNetwork.SIGNAL_NODE_NAMING,        self.notif_node_named),
            (ZWaveNetwork.SIGNAL_NODE_REMOVED,       self.notif_node_removed),
            (ZWaveNetwork.SIGNAL_VALUE_ADDED,        self.notif_value_added),
            (ZWaveNetwork.SIGNAL_VALUE_CHANGED,      self.notif_value_update),
            (ZWaveNetwork.SIGNAL_VALUE_REMOVED,      self.notif_value_removed),
            (ZWaveNetwork.SIGNAL_CONTROLLER_COMMAND, self.notif_ctrl_message),
            (ZWaveNetwork.SIGNAL_CONTROLLER_WAITING, self.notif_ctrl_message),
        ]
        for notif, func in notif_to_func:
            dispatcher.connect(self._notif_wrapper(func), notif, weak=False)

        # dispatcher.connect(self._notif_wrapper_all, All)

        self.isac_node.add_rpc(self.network_heal)
        self.isac_node.add_rpc(self.controller_add_node, name='add_node')
        self.isac_node.add_rpc(self.controller_remove_node, name='remove_node')
        self.isac_node.add_rpc(self.controller_cancel_command, name='cancel_command')

    # Plumbing

    def _notif_wrapper(self, f):
        def _notif(*args, **kwargs):
            logger.debug('Received notification for %s with args %s and kwargs %s', f.__name__, args, kwargs)
            del kwargs['signal']
            del kwargs['sender']
            self._ozw_notif_queue.put((f, args, kwargs))

        return _notif

    def _notif_wrapper_all(self, *args, **kwargs):
        del kwargs['sender']
        self._ozw_notif_queue.put((self.all_notif, args, kwargs))

    def _notif_reader(self):
        while self._running:
            notif = self._ozw_notif_queue.get()
            if notif is None:
                continue

            f, args, kwargs = notif
            logger.debug('Reading notification for %s with args %s and kwargs %s', f.__name__, args, kwargs)
            f(*args, **kwargs)

    def all_notif(self, *args, **kwargs):
        import time
        from pprint import pformat as pf
        extra = []
        if 'value' in kwargs and kwargs['value']:
            extra.append('value: %s' % self._make_uri(kwargs['node'], kwargs['value']))
        elif 'node' in kwargs and kwargs['node']:
            extra.append('node: %s' % (kwargs['node'].name if kwargs['node'].name else kwargs['node'].node_id))
        extra = ' ; '.join(extra)

        if args:
            logger.warning('>~>~># %f: %s ; %s ; %s', time.time(), pf(args), pf(kwargs), extra)
        else:
            logger.warning('>~>~># %f: %s ; %s', time.time(), pf(kwargs), extra)

    # Notifications from PYOZW

    def notif_network_started(self, network):
        logger.info('//////////// ZWave network is started ////////////')
        logger.debug(
            'OpenZWave network is started: \
            homeid %0.8x - %d nodes were found.',
            network.home_id, network.nodes_count
        )

    def notif_network_resetted(self, network):
        logger.warning('OpenZWave network is resetted.')

    def notif_network_ready(self, network):
        logger.info('//////////// ZWave network is ready ////////////')
        logger.debug(
            'ZWave network is ready: %d nodes were found.',
            network.nodes_count
        )

    def notif_node_added(self, network, node):
        node_name = self._node_name(node)
        logger.info('Node added: %s.', node_name)
        self.isac_node.add_rpc(partial(self.node_heal, node), '%s/heal' % node_name)
        self.isac_node.add_rpc(partial(self.node_is_failed, node), '%s/is_failed' % node_name)

    def notif_node_named(self, network, node):
        logger.info('Node named: %s.', self._node_name(node))
        # TODO: renaming of RPC enpoints as well as all IsacValue attached to the node, if the name really changed

    def notif_node_removed(self, network, node):
        logger.info('Node removed: %s.', self._node_name(node))
        # TODO: Remove RPC endpoint (values should be removed by receiving VALUE_REMOVED notif)

    def notif_value_added(self, network, node, value):
        uri = self._make_uri(node, value)

        if uri in self.signals:
            logger.info('%s already registered', uri)
            return
        else:
            logger.info('Registering signal %s', uri)

        self.signals[uri] = {
            'metadata': {
                'uri': uri,
                'label': value.label,
                'help': value.help,
                'max': value.max,
                'min': value.min,
                'units': value.units,
                'genre': value.genre,
                'type': value.type,
                'is_read_only': value.is_read_only,
                'is_write_only': value.is_write_only,
                'instance': value.instance,
                'index': value.index,
                'value_id': value.value_id,
                'node_id': node.node_id,
                'node_name': node.name,
                'location': node.location,
                'home_id': node._network.home_id,
                'command_class': node.get_command_class_as_string(value.command_class),
                'data_items':
                    list(value.data_items)
                    if type(value.data_items) is set
                    else value.data_items,
            },
            'static_tags': {
                'home_id': node._network.home_id,
                'location': node.location,
                'node_id': node.node_id,
                'command_class': node.get_command_class_as_string(value.command_class),
                'index': value.index,
                'instance': value.instance,
            },
            'node_value': (node, value),
        }

        data = self._value_data(value)

        #print '>>>> Creating IV', uri, data
        self.signals[uri]['isac_value'] = IsacValue(
            self.isac_node, uri, data,
            static_tags=self.signals[uri]['static_tags'],
            metadata=self.signals[uri]['metadata'],
            survey_last_value=False,
            survey_static_tags=False
        )
        self.signals[uri]['isac_value'].observers += self._update_data_from_isac

        uri_poll = uri + '/poll'
        self.signals[uri_poll] = {
            'isac_value': IsacValue(
                self.isac_node, uri_poll, value.is_polled,
                survey_last_value=False, survey_static_tags=False
            ),
            'node_value': self.signals[uri]['node_value'],
        }
        self.signals[uri_poll]['isac_value'].observers += self._set_poll_from_isac

    def notif_value_update(self, network, node, value):
        uri = self._make_uri(node, value)

        logger.info('Value update for %s : %s.', uri, value.data)

        if uri not in self.signals:
            logger.info('%s not yet registered, skipping', uri)
            return

        signal = self.signals[uri]

        signal['isac_value'].value = self._value_data(value)

    def notif_value_removed(self, network, node, value):
        pass
        # TODO: Remove IsacValue

    def notif_ctrl_message(self, network, controller, **kwargs):
        # from pprint import pformat as pf
        # logger.warning('Controller message : %s', pf(kwargs))
        pass

    # Update from ISAC

    def _update_data_from_isac(self, isac_value, value, ts, tags):
        uri = isac_value.uri
        signal = self.signals.get(uri, None)
        if signal is None:
            logger.error(
                'Received an update from isac \
                for a signal we don\'t know?! %s',
                uri
            )
            return

        if signal['node_value'][1].is_read_only:
            logger.error(
                'Signal %s is read only but we received an update \
                from isac to write a value, %s, to it',
                uri,
                value
            )
            return

        logger.info('Updating value %s with %s', uri, value)
        signal['node_value'][1].data = value

    def _set_poll_from_isac(self, isac_value, value, ts, tags):
        uri = isac_value.uri
        signal = self.signals.get(uri, None)
        if signal is None:
            logger.error('Signal %s is unknown?!', uri)
            return

        if uri.endswith('/poll'):
            if bool(value):
                try:
                    intensity = int(value)
                except ValueError:
                    intensity = 1

                signal['node_value'][1].enable_poll(intensity)
            else:
                signal['node_value'][1].disable_poll()

    # RPC methods

    # controller: (hard_reset) has_node_failed(nodeid) name remove_failed_node(nodeid) replace_failed_node(nodeid) (soft_reset)
    # node: location name

    # def has_node_failed(self, node_name):
    #     from pprint import pprint as pp
    #     nodes_by_name = {node.name: node for node in self.network.nodes.values()}
    #     pp(nodes_by_name)
    #     node_id = nodes_by_name[node_name].node_id
    #
    #     print nodes_by_name[node_name].is_failed
    #     return self.network.controller.has_node_failed(node_id)

    def network_heal(self, upNodeRoute=False):
        logger.info('Healing network')
        self.network.heal(upNodeRoute)

    def controller_add_node(self, doSecurity=False):
        logger.info('Set controller into inclusion mode')
        return self.network.controller.add_node(doSecurity)

    def controller_remove_node(self):
        logger.info('Set controller into exclusion mode')
        return self.network.controller.remove_node()

    def controller_cancel_command(self):
        logger.info('Cancelling controller command')
        return self.network.controller.cancel_command()

    def node_heal(self, node, upNodeRoute=False):
        logger.info('Healing node %s', self._node_name(node))
        return node.heal(upNodeRoute)

    def node_is_failed(self, node):
        logger.info('Asking if node %s is failed (%s)', self._node_name(node), node.is_failed)
        return node.is_failed

    # Tooling

    @staticmethod
    def _replace_all(s, olds, new):
        return reduce(lambda s, old: s.replace(old, new), list(olds), s)

    def _node_name(self, node):
        return node.name if node.name else str(node.node_id)

    def _value_data(self, value):
        data = value.data
        logger.debug('data type is %s', type(data))
        if type(data) is str:
            try:
                data.decode()
            except UnicodeDecodeError:
                data = binascii.b2a_base64(data)

        return data

    def _make_uri(self, node, value):

        def _values_by_index(values):
            per_idx = {}
            for value in values:
                idx = value.index
                if idx not in per_idx:
                    per_idx[idx] = []
                per_idx[idx].append(value)
            return per_idx

        ok = False
        while not ok:
            try:
                values_by_idx = _values_by_index(node.get_values(class_id=value.command_class).values())
                ok = True
            except RuntimeError as ex:
                if ex.message == 'dictionary changed size during iteration':
                    continue
                else:
                    raise

        is_multi_instance = len(values_by_idx[value.index]) > 1

        cmd_class = node.get_command_class_as_string(value.command_class)
        cmd_class = cmd_class.replace('COMMAND_CLASS_', '').lower()

        node_name = self._node_name(node)
        label = self._replace_all(value.label.lower(), ' /()%:', '_').strip('_')

        if is_multi_instance:
            uri = 'zwave://%s.%s/%s/%d/%s' % (
                node._network.home_id_str, node_name, cmd_class, value.instance, label)
        else:
            uri = 'zwave://%s.%s/%s/%s' % (
                node._network.home_id_str, node_name, cmd_class, label)

        return str(uri)

    # Lifecycle

    def shutdown(self):
        # Stopping internal notification reader greenlet
        self._running = False
        self._ozw_notif_queue.put(None)

        self.network.stop()
        logger.info('Stopped network')
        self.network.destroy()
        logger.info('Destroyed network')
        self.isac_node.shutdown()
        logger.info('Stopped ISAC node')


def sigterm_handler(alidron_ozw):
    logger.info('Received SIGTERM signal, exiting')
    alidron_ozw.shutdown()
    logger.info('Exiting')
    sys.exit(0)


if __name__ == '__main__':
    DEVICE = sys.argv[1]

    isac_node = IsacNode('alidron-openzwave-controller')

    alidron_ozw = AlidronOZW(DEVICE, isac_node)

    green.signal(signal.SIGTERM, partial(sigterm_handler, alidron_ozw))

    try:
        isac_node.serve_forever()
    except KeyboardInterrupt:
        alidron_ozw.shutdown()
        green.sleep(1)
