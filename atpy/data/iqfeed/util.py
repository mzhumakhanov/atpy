import numpy as np
import pyiqfeed as iq
from passwords import dtn_product_id, dtn_login, dtn_password
import queue
import threading


def launch_service():
    """Check if IQFeed.exe is running and start if not"""

    svc = iq.FeedService(product=dtn_product_id,
                         version="Debugging",
                         login=dtn_login,
                         password=dtn_password)
    svc.launch()


def create_batch(data, column_mode=True, key_suffix=''):
    """
    Create minibatch-type data based on the pyiqfeed data format
    :param data: data list
    :param column_mode: whether to convert the data to column mode (or row mode)
    :return:
    """
    if column_mode:
        for i, datum in enumerate(data):
            if len(datum) == 1:
                datum = datum[0]

            if i == 0:
                result = {n + key_suffix: np.empty((len(data),), d.dtype) for n, d in zip(datum.dtype.names, datum)}

            for j, f in enumerate(datum.dtype.names):
                result[f][i] = datum[j]
    else:
        result = list()
        for datum in data:
            result.append(iqfeed_to_dict(datum, key_suffix))

    return result


def iqfeed_to_dict(data, key_suffix=''):
    """
    Turn one iqfeed data item to dict
    :param data: data list
    :param key_suffix: suffix to each name
    :return:
    """
    if len(data) == 1:
        data = data[0]

    return {n + key_suffix: d for n, d in zip(data.dtype.names, data)}


class IQFeedDataProvider(object):
    """Streaming data provider generator/iterator interface"""

    def __init__(self, producer):
        self._queue = queue.Queue()
        self._producer = producer
        self._lock = threading.RLock()

        with self._lock:
            self._is_listening = True
            producer += self._populate_queue

    def _populate_queue(self, event):
        self._queue.put(event['data'])

    def __iter__(self):
        return self

    def __next__(self) -> map:
        return self._queue.get()

    def __enter__(self):
        with self._lock:
            if not self._is_listening:
                self._is_listening = True
                self._producer += self._populate_queue

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        with self._lock:
            if self._is_listening:
                self._is_listening = False
                self._producer -= self._populate_queue