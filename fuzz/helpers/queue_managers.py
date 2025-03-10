import json
import time
from typing import List

import pika


class QueueManager:
    def __init__(self, host, port, queue_name, logger):
        self.host = host
        self.port = port
        self.__attempts_count = 0
        self.logger = logger

        # TODO: it's supposed to be refactored to support different QM's
        self._connection = self.__connect()
        self.logger.info("successful connection after %s attempts", self.__attempts_count)

        self.channel = self._connection.channel()
        self._queue_name = queue_name

        self.channel.queue_declare(queue_name, durable=True)

    def __connect(self):
        try:
            return pika.BlockingConnection(pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                heartbeat=0
            ))
        except pika.exceptions.AMQPConnectionError as e:
            attempt = self._attempts_counter
            if attempt < 20:
                # print("connect failed, attempt number {}".format(attempt), flush=True)
                self.logger.info("connect failed, attempt number %s", attempt)
                time.sleep(5)
                return self.__connect()
            raise e

    @property
    def _attempts_counter(self):
        self.__attempts_count += 1
        return self.__attempts_count

    def publish(self, **kwargs):
        message = json.dumps(kwargs)
        self.channel.basic_publish(
            exchange='',
            routing_key=self._queue_name,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent
            )
        )


class MultiQueueManager:
    def __init__(self, queue_managers: List[QueueManager] = None):
        self.queue_managers = queue_managers if queue_managers is not None else []

    def publish(self, **kwargs):
        for queue in self.queue_managers:
            queue.publish(**kwargs)
