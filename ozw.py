import binascii
import logging
import os
import signal
import sys
from functools import partial
from pprint import pprint as pp, pformat as pf

from louie import dispatcher
# from openzwave.node import ZWaveNode
# from openzwave.value import ZWaveValue
# from openzwave.scene import ZWaveScene
from openzwave.controller import ZWaveController
from openzwave.network import ZWaveNetwork
from openzwave.option import ZWaveOption

import gevent

from isac import IsacNode, IsacValue


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)

logger.info('Starting')


class AlidronOZW(object):

    def __init__(self, device, isac_node):
        self.isac_node = isac_node

        self.signals = {}

        self.options = ZWaveOption(
            device,
            #config_path='/usr/src/python-openzwave-0.2.6/openzwave/config',
            #config_path='/usr/src/python-openzwave-0.3.0-beta2/openzwave/config',
            #config_path='/usr/src/python-openzwave-{0}/openzwave/config'.format(os.environ['PYOZW_VERSION']),
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

        dispatcher.connect(self.louie_network_started,
                           ZWaveNetwork.SIGNAL_NETWORK_STARTED)
        dispatcher.connect(self.louie_network_resetted,
                           ZWaveNetwork.SIGNAL_NETWORK_RESETTED)
        dispatcher.connect(self.louie_network_ready,
                           ZWaveNetwork.SIGNAL_NETWORK_READY)
        dispatcher.connect(self.louie_node_update,
                           ZWaveNetwork.SIGNAL_NODE)
        dispatcher.connect(self.louie_value_update,
                           ZWaveNetwork.SIGNAL_VALUE)
        dispatcher.connect(self.louie_ctrl_message,
                           ZWaveController.SIGNAL_CONTROLLER)

        gevent.sleep(3)

        self.register_all_nodes()

    def louie_network_started(self, network):
        logger.warning('//////////// ZWave network is started ////////////')
        logger.debug(
            'OpenZWave network is started : \
            homeid %0.8x - %d nodes were found.',
            network.home_id, network.nodes_count
        )

    def louie_network_resetted(self, network):
        logger.warning('OpenZWave network is resetted.')

    def louie_network_ready(self, network):
        logger.warning('//////////// ZWave network is ready ////////////')
        logger.debug(
            'ZWave network is ready : %d nodes were found.',
            network.nodes_count
        )
        logger.debug('Controller : %s', network.controller)

        dispatcher.connect(self.louie_node_update, ZWaveNetwork.SIGNAL_NODE)
        dispatcher.connect(self.louie_value_update, ZWaveNetwork.SIGNAL_VALUE)
        dispatcher.connect(self.louie_ctrl_message,
                           ZWaveController.SIGNAL_CONTROLLER)

    def louie_node_update(self, network, node):
        logger.debug('Node update : %s.', node)
        self.register_all_values(node)

    def louie_value_update(self, network, node, value):
        uri = self._make_uri(node, value)

        logger.info('Value update for %s : %s.', uri, value.data)

        if uri not in self.signals:
            logger.info('%s not yet registered, skipping', uri)
            return

        signal = self.signals[uri]

        data = value.data
        logger.info('data type is %s', type(data))
        if type(data) is str:
            try:
                data.decode()
            except UnicodeDecodeError:
                data = binascii.b2a_base64(data)

        signal['isac_value'].value = data

    def louie_ctrl_message(self, state, message, network, controller):
        logger.warning('Controller message : %s.', message)

    def register_all_values(self, node):
        # def _data(value, *args, **kwargs):
        #    if not args:
        #        if ('refresh' in kwargs) and kwargs['refresh']:
        #            if value.is_write_only:
        #                raise Exception('Cannot refresh a write only node value')
        #
        #            value.refresh()
        #        return value.data
        #
        #    else:
        #        if value.is_read_only:
        #            raise Exception('Cannot write to a read only node')
        #
        #        value.data = args[0]

        def _set_data(isac_value, value, ts, tags):
            uri = isac_value.uri
            if uri not in self.signals:
                logger.error(
                    'Received an update from isac \
                    for a signal we don\'t know?! %s',
                    uri
                )
                return

            signal = self.signals[uri]

            if signal['node_value'][1].is_read_only:
                logger.error(
                    'Signal %s is read only but we received an update \
                    from isac to write a value, %s, to it',
                    uri,
                    value
                )
                return

            signal['node_value'][1].data = value

        for value in node.values.values():
            uri = self._make_uri(node, value)

            if uri in self.signals:
                logger.info('%s already registered', uri)
                continue
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

        for uri, signal in self.signals.items():
            if 'isac_value' in signal:
                continue

            data = signal['node_value'][1].data
            logger.info('data type is %s', type(data))
            if type(data) is str:
                try:
                    data.decode()
                except UnicodeDecodeError:
                    data = binascii.b2a_base64(data)

            #print '>>>> Creating IV', uri, data
            signal['isac_value'] = IsacValue(
                self.isac_node,
                str(uri),
                data,
                static_tags=signal['static_tags'],
                metadata=signal['metadata'],
                survey_last_value=False,
                survey_static_tags=False
            )
            signal['isac_value'].observers += _set_data

            gevent.sleep(0.01)

    def register_all_nodes(self):
        for node in self.network.nodes.values():
            logger.debug('Registering all values from node %s', node.name)
            self.register_all_values(node)

    @staticmethod
    def _replace_all(s, olds, new):
        return reduce(lambda s, old: s.replace(old, new), list(olds), s)

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

        node_name = node.name if node.name else str(node.node_id)
        label = self._replace_all(value.label.lower(), ' /()%:', '_').strip('_')

        if is_multi_instance:
            uri = 'zwave://%s.%s/%s/%d/%s' % (
                node._network.home_id_str, node_name, cmd_class, value.instance, label)
        else:
            uri = 'zwave://%s.%s/%s/%s' % (
                node._network.home_id_str, node_name, cmd_class, label)

        return uri

    def shutdown(self):
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

    gevent.signal(signal.SIGTERM, partial(sigterm_handler, alidron_ozw))

    isac_node.serve_forever()


# @server.register
def stop_network():
    print 'Stopping'
    network.stop()

    def _shutdown():
        print 'Shutting down'
        server.shutdown()
    gevent.spawn_later(0.5, _shutdown)
    print 'Returns'


# @server.register(name='list')
def list_procs():
    return signal_list
