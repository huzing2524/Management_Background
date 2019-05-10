# -*- coding: utf-8 -*-
import time
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bg.utils import AliOss, generate_uuid
from apps_utils import UtilsPostgresql, UtilsRabbitmq
from constants import START_TIME

logger = logging.getLogger('django')


# V3.4.0----------------------------------------------------------------------------------------------------------------

class BgInviteFactoryList(APIView):
    """邀请企业列表 /bg/invite/factory/list"""

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        invite_phone = request.query_params.get('invite_phone', '')
        admin_phone = request.query_params.get('admin_phone', '')
        row = request.query_params.get('row', '10')
        page = request.query_params.get('page', '1')

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        if invite_phone and admin_phone:
            condition = "where t2.invitor_id is not NULL and t2.invitor_id like '%{}%' and " \
                        "array_to_string(administrators, ',', '*') like '%{}%'".format(invite_phone, admin_phone)
        elif invite_phone:
            condition = "where t2.invitor_id is not NULL and t2.invitor_id like '%{}%'".format(invite_phone)
        elif admin_phone:
            condition = "where t2.invitor_id is not NULL and array_to_string(administrators, ',', '*') like '%{}%' ".format(admin_phone)
        else:
            condition = 'where t2.invitor_id is not NULL'

        sql = "select * from(select t2.invitor_id, t1.name, administrators, t2.time, t3.name, t1.time, t1.state, " \
              "row_number() over (order by t2.time desc) as rn from bg_examine t1 left join user_info t2 on t1.id = " \
              "t2.phone left join user_info t3 on t2.invitor_id = t3.phone left join factory_users t4 on t1.id = " \
              "t4.phone left join factorys t5 on t4.factory = t5.id {})t where rn > {} order by rn asc limit {};".format(condition, offset, limit)
        sql_count = "select count(1) from(select t2.invitor_id, t1.name, administrators, t2.time, t3.name, t1.time, " \
                    "t1.state, row_number() over (order by t1.time desc) as rn from bg_examine t1 left join user_info" \
                    " t2 on t1.id = t2.phone left join user_info t3 on t2.invitor_id = t3.phone left join " \
                    "factory_users t4 on t1.id = t4.phone left join factorys t5 on t4.factory = t5.id {})t;".format(condition)

        target = ['invite_phone', 'factory', 'admin_phone', 'time', 'invite_name', 'verify_time', 'state', 'rn']

        try:
            cur.execute(sql)
            data = [dict(zip(target, i)) for i in cur.fetchall()]
            cur.execute(sql_count)
            total = cur.fetchone()[0]
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        for i in data:
            if i['admin_phone'] is None:
                i['admin_phone'] = []
            if i['invite_name'] is None:
                i['invite_name'] = ''
            # '0' 代表获得奖励， '1' 代表未获得奖励
            # 在这个时间前，默认已获得奖励
            if i['time'] <= START_TIME:
                i['reward'] = '0'
            # 之后，邀请企业60天以内通过认证认为已获得奖励
            elif i['verify_time'] - i['time'] <= 5184000 and i['state'] == '3':
                i['reward'] = '0'
            else:
                i['reward'] = '1'
            del i['state']
            del i['verify_time']

        postgresql.disconnect_postgresql(conn)
        return Response({'data': data, 'total': total}, status=status.HTTP_200_OK)


class BgInviteFriendList(APIView):
    """邀请好友列表 /bg/invite/friend/list"""

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        invite_phone = request.query_params.get('invite_phone', '')
        invited_phone = request.query_params.get('invited_phone', '')
        row = request.query_params.get('row', '10')
        page = request.query_params.get('page', '1')

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        if invite_phone and invited_phone:
            condition = "where t1.invitor_id is not NULL and t1.phone like '%{}%' and t1.invitor_id like '%{}%' ".format(invited_phone, invite_phone)
        elif invited_phone:
            condition = "where t1.invitor_id is not NULL and t1.phone like '%{}%'".format(invited_phone)
        elif invite_phone:
            condition = "where t1.invitor_id is not NULL and t1.invitor_id like '%{}%' ".format(invite_phone)
        else:
            condition = "where t1.invitor_id is not NULL"

        sql = "select * from(select t1.phone, t1.name, t1.invitor_id, t1.time, t2.name, t3.time, t1.auth_state, " \
              "row_number() over (order by t1.time desc) as rn from user_info t1 left join user_info t2 on t1.invitor" \
              "_id = t2.phone left join user_auth t3 on t1.phone = t3.phone {})t where rn > {} order by rn asc limit" \
              " {};".format(condition, offset, limit)
        sql_count = "select count(1) from(select t1.phone, t1.name, t1.invitor_id, t1.time, t2.name, t3.time, " \
                    "row_number() over (order by t1.time desc) as rn from user_info t1 left join user_info t2 on " \
                    "t1.invitor_id = t2.phone left join user_auth t3 on t1.phone = t3.phone {})t ;".format(condition)
        target = ['invited_phone', 'invited_name', 'invite_phone', 'invite_time', 'invite_name', 'verify_time',
                  'auth_state', 'rn']

        try:
            cur.execute(sql)
            data = [dict(zip(target, i)) for i in cur.fetchall()]
            cur.execute(sql_count)
            total = cur.fetchone()[0]
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        for i in data:
            if i['invited_name'] is None:
                i['invited_name'] = ''
            if i['invite_phone'] is None:
                i['invite_phone'] = ''
            if i['invite_name'] is None:
                i['invite_name'] = ''
            # '0' 代表获得奖励， '1' 代表未获得奖励
            # 在这个时间前，默认已获得奖励
            if i['invite_time'] <= START_TIME:
                i['reward'] = '0'
            elif not i['verify_time']:
                i['reward'] = '1'
            # 之后，邀请好友30天以内通过认证认为已获得奖励
            elif i['verify_time'] - i['invite_time'] <= 2592000 and i['auth_state'] == 3:
                i['reward'] = '0'
            else:
                i['reward'] = '1'

            del i['auth_state']

        postgresql.disconnect_postgresql(conn)
        return Response({'data': data, 'total': total}, status=status.HTTP_200_OK)


class BgBanner(APIView):
    """get: 获取banner列表 /bg/banner"""
    """post: 新增banner图片 /bg/banner"""
    """put: 修改banner图片/状态（上架或下架） /bg/banner"""
    """delete: 删除banner图片 /bg/banner"""

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        alioss = AliOss()

        row = request.query_params.get('row', '10')
        page = request.query_params.get('page', '1')

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        sql = "select * from (select *, row_number() over (order by time desc) as rn from bg_banner)t where rn > {} " \
              "order by rn asc limit {};".format(offset, limit)
        sql_count = "select count(1) from (select *, row_number() over (order by time desc) as rn from bg_banner)t;"
        target = ['id', 'image', 'state', 'time', 'rn']

        try:
            cur.execute(sql)
            data = []
            for i in cur.fetchall():
                tmp = dict(zip(target, i))
                tmp['image'] = alioss.joint_image(tmp['image'])
                data.append(tmp)
            cur.execute(sql_count)
            total = cur.fetchone()[0]
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        postgresql.disconnect_postgresql(conn)
        return Response({'data': data, 'total': total}, status=status.HTTP_200_OK)

    def post(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        alioss = AliOss()

        image = request.data.get('image')

        Time = int(time.time())
        uuid = generate_uuid()
        image = alioss.upload_image(image)[0]
        sql = "insert into bg_banner values('{}', '{}', '1', {});".format(uuid, image, Time)

        try:
            cur.execute(sql)
            conn.commit()
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        postgresql.disconnect_postgresql(conn)
        return Response({'res': 0}, status=status.HTTP_200_OK)

    def put(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        alioss = AliOss()

        Id = request.data.get('id')
        state = request.data.get('state')
        image = request.data.get('image')

        if state is not None:
            sql_0 = ''
            sql = "update bg_banner set state = '%s' where id = '%s';" % (state, Id)
        elif image is not None:
            # 没有修改图片
            if 'https://' in image:
                postgresql.disconnect_postgresql(conn)
                return Response({'res': 0}, status=status.HTTP_200_OK)
            sql_0 = "select image from bg_banner where id = '%s';" % Id
            new_image_id = alioss.upload_image(image)[0]
            sql = "update bg_banner set image = '%s' where id = '%s';" % (new_image_id, Id)

        try:
            if sql_0:
                cur.execute(sql_0)
                image_id = cur.fetchone()[0]
                alioss.delete_image(image_id)
            cur.execute(sql)
            conn.commit()
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        postgresql.disconnect_postgresql(conn)
        return Response({'res': 0}, status=status.HTTP_200_OK)

    def delete(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        alioss = AliOss()

        Id = request.query_params.get('id')

        sql_0 = "select image from bg_banner where id = '%s';" % Id
        sql_1 = "delete from bg_banner where id = '%s';" % Id

        try:
            cur.execute(sql_0)
            image_id = cur.fetchone()[0]
            alioss.delete_image(image_id)
            cur.execute(sql_1)
            conn.commit()
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        postgresql.disconnect_postgresql(conn)
        return Response({"res": 0}, status=status.HTTP_200_OK)

