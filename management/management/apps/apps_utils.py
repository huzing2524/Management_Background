# -*- coding: utf-8 -*-
import pika
from constants import BG_QUEUE_NAME
from psycopg2.pool import AbstractConnectionPool

from django.conf import settings


class UtilsPostgresql(AbstractConnectionPool):
    """数据库连接池"""

    def __init__(self):
        super().__init__(minconn=5, maxconn=20, database=settings.POSTGRESQL_DATABASE, user=settings.POSTGRESQL_USER,
                         password=settings.POSTGRESQL_PASSWORD, host=settings.POSTGRESQL_HOST,
                         port=settings.POSTGRESQL_PORT)

    def connect_postgresql(self):
        connection = AbstractConnectionPool._getconn(self)
        cursor = connection.cursor()
        # print(connection)
        return connection, cursor

    def disconnect_postgresql(self, connection):
        AbstractConnectionPool._putconn(self, connection)


class UtilsRabbitmq(object):
    """RabbitMQ消息发送"""
    host = settings.RABBITMQ_HOST
    port = settings.RABBITMQ_PORT
    vhost = '/'

    @classmethod
    def _connect_rabbitmq(cls):
        """连接rabbitmq"""
        try:
            parameters = pika.ConnectionParameters(host=cls.host, port=cls.port)
            connection = pika.BlockingConnection(parameters)
            return connection
        except Exception as e:
            raise e

    @classmethod
    def _disconnect_rabbitmq(cls, connection):
        """关闭连接"""
        connection.close()

    def send_message(self, message):
        """发送消息"""
        conn = self._connect_rabbitmq()
        channel = conn.channel()
        channel.basic_publish(exchange='', routing_key=BG_QUEUE_NAME, body=message)
        # print('send %s' % message)
        self._disconnect_rabbitmq(conn)

    def recieve_message(self):
        """接收消息"""
        conn = self._connect_rabbitmq()
        channel = conn.channel()
        channel.queue_declare(queue=BG_QUEUE_NAME)

        def callback(ch, method, properties, body):
            print('[x] recieved %r' % body)

        channel.basic_consume(callback, queue=BG_QUEUE_NAME, no_ack=True)
        channel.start_consuming()
