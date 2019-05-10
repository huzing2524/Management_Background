# -*- coding: utf-8 -*-
import json
import logging
import re
import time
import jwt

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from apps_utils import UtilsPostgresql, UtilsRabbitmq
from bg.utils import AliOss, generate_uuid
from constants import RIGHTS_DICT, EDIT_RIGHTS_LIST

logger = logging.getLogger('django')


# V3.1.0----------------------------------------------------------------------------------------------------------------

class BgRightsList(APIView):
    """权限展示列表 /bg/rights/list"""

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        phone = request.query_params.get('phone', '')
        username = request.query_params.get('username', '')
        name = request.query_params.get('name', '')
        row = request.data.get('row', '10')
        page = request.data.get('page', '1')

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        p_1 = "phone like '%{}%' and ".format(phone) if phone else ''
        p_2 = "username like '%{}%' and ".format(username) if username else ''
        p_3 = "name like '%{}%' and".format(name) if name else ''
        part_sql = p_1 + p_2 + p_3

        sql = "select * from(select phone, username, name, row_number() over (order by time desc) as rn from " \
              "bg_user where {} rights = '1')t where rn > {} order by rn asc limit {};".format(part_sql, offset, limit)
        # print(sql)
        sql_count = "select count(1) from(select phone, username, name, row_number() over (order by time desc) as rn" \
                    " from bg_user where {} rights = '1')t;".format(part_sql)
        target = ['phone', 'username', 'name', 'rn']

        try:
            cur.execute(sql)
            tmp_0 = cur.fetchall()
            cur.execute(sql_count)
            tmp_1 = cur.fetchone()
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        data = []
        for i in tmp_0:
            data.append(dict(zip(target, i)))
        total = tmp_1[0]

        postgresql.disconnect_postgresql(conn)
        return Response({'data': data, 'total': total}, status=status.HTTP_200_OK)


class BgRightsNew(APIView):
    """新增管理员 /bg/rights/new"""

    def post(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        token = request.META.get("HTTP_AUTHORIZATION")
        token = token.split(" ")[-1]
        payload = jwt.decode(token, settings.SECRET_KEY)

        user = payload['username']
        phone = request.data.get('phone')
        name = request.data.get('name', '')
        Time = int(time.time())

        # 判断是手机号还是用户名
        if user.isdigit() and len(user) == 11:
            login_type = 'phone'
        else:
            login_type = 'username'
        if not re.match("^(13[0-9]|14[579]|15[0-3,5-9]|16[6]|17[0135678]|18[0-9]|19[89])\\d{8}$", phone):
            return Response({'res': 1, 'errmsg': "手机号输入格式有误"}, status=status.HTTP_200_OK)

        # 手机号不能重复
        sql_phone = "select count(1) from bg_user where phone = '%s';" % phone
        # 判断权限
        sql_right = "select rights from bg_user where %s = '%s';" % (login_type, user)
        try:
            cur.execute(sql_phone)
            tmp_0 = cur.fetchone()[0]
            cur.execute(sql_right)
            tmp_1 = cur.fetchone()
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if tmp_0:
            return Response({'res': 1, 'errmsg': "手机号已存在"}, status=status.HTTP_200_OK)
        # 权限不足,非超级管理员
        if tmp_1[0] != '0':
            return Response({'res': 1, 'errmsg': "对不起，您没有此操作的权限！"}, status=status.HTTP_200_OK)

        # 默认密码 123456
        username = generate_uuid()[:11]
        sql_0 = "insert into bg_user(username, phone, name, time, password) values('%s', '%s', '%s', %d, " \
                "crypt('123456', gen_salt('bf')));" % (username, phone, name, Time)

        try:
            cur.execute(sql_0)
            conn.commit()
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        postgresql.disconnect_postgresql(conn)
        return Response({"res": 0}, status=status.HTTP_200_OK)


class BgRightsDel(APIView):
    """删除管理员 /bg/rights/del"""

    def delete(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        token = request.META.get("HTTP_AUTHORIZATION")
        token = token.split(" ")[-1]
        payload = jwt.decode(token, settings.SECRET_KEY)

        user = payload['username']
        phone = request.query_params.get('phone')

        # 判断是手机号还是用户名
        if re.match("^(13[0-9]|14[579]|15[0-3,5-9]|16[6]|17[0135678]|18[0-9]|19[89])\\d{8}$", phone):
            login_type = 'phone'
        else:
            login_type = 'username'

        sql = "select rights from bg_user where %s = '%s';" % (login_type, user)
        try:
            cur.execute(sql)
            tmp = cur.fetchone()
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # 权限不足,非超级管理员
        if tmp[0] != '0':
            return Response({'res': 1, 'errmsg': "对不起，您没有此操作的权限！"}, status=status.HTTP_200_OK)

        sql_0 = "delete from bg_user where phone = '%s';" % phone
        try:
            cur.execute(sql_0)
            conn.commit()
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        postgresql.disconnect_postgresql(conn)
        return Response({"res": 0}, status=status.HTTP_200_OK)


class BgRightsPassword(APIView):
    """修改管理员密码 /bg/rights/password"""

    def put(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        token = request.META.get("HTTP_AUTHORIZATION")
        token = token.split(" ")[-1]
        payload = jwt.decode(token, settings.SECRET_KEY)

        user = payload['username']
        old_password = request.data.get('old_password', '')
        new_password = request.data.get('new_password', '')

        if not old_password or not new_password:
            return Response({'res': 1, 'errmsg': "密码不能为空"}, status=status.HTTP_200_OK)

        # 判断是手机号还是用户名
        if re.match("^(13[0-9]|14[579]|15[0-3,5-9]|16[6]|17[0135678]|18[0-9]|19[89])\\d{8}$", user):
            login_type = 'phone'
        else:
            login_type = 'username'

        sql_0 = "select count(1) from bg_user where %s = '%s' and password = crypt('%s', password);" \
                % (login_type, user, old_password)
        try:
            cur.execute(sql_0)
            tmp = cur.fetchone()
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        check = tmp[0]
        if not check:
            return Response({"res": 1, "errmsg": "密码错误"}, status=status.HTTP_200_OK)

        sql_1 = "update bg_user set password = crypt('%s', gen_salt('bf')) where %s = '%s';" % (new_password,
                                                                                                login_type, user)
        try:
            cur.execute(sql_1)
            conn.commit()
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        postgresql.disconnect_postgresql(conn)
        return Response({"res": 0}, status=status.HTTP_200_OK)


class BgRightsName(APIView):
    """修改管理员名字 /bg/rights/name"""

    def put(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        phone = request.data.get('phone')
        new_name = request.data.get('new_name', '')

        sql_0 = "update bg_user set name = '%s' where phone = '%s';" % (new_name, phone)
        try:
            cur.execute(sql_0)
            conn.commit()
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        postgresql.disconnect_postgresql(conn)
        return Response({"res": 0}, status=status.HTTP_200_OK)


class FactoryList(APIView):
    """后台企业列表 /facs/list
    factory_users.rights = '{1}' 为超级管理员
    bg_examine.state = 3 审核通过
    bg_examine.state = 2 审核不通过
    """

    def get(self, request):
        row = int(request.query_params.get("row", 10))  # 每页数量(默认值为10)
        page = int(request.query_params.get("page", 1))  # 当前页数(默认值为1)
        company_name = request.query_params.get("company_name")  # 公司名称
        administrators = request.query_params.get("administrators")  # 超级管理员
        offset = row * (page - 1)

        condition = ""
        if company_name and not administrators:
            condition += " where title like '%" + company_name + "%' "
        elif administrators and not company_name:
            condition += "where array_to_string(administrators, ',', '*') like '%" + administrators + "%' "
        elif company_name and administrators:
            condition += " where title like '%" + company_name + "%' and array_to_string(administrators, ',', '*')" \
                                                                 " like '%" + administrators + "%' "
        # print(condition)

        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        alioss = AliOss()
        try:
            sql_count = "select count(1) from (select row_number() over (order by t1.time desc) as rn, t1.time," \
                        " t1.id, t1.title, t1.administrators, t2.industry, t2.region, t2.contact, t2.image1," \
                        " t2.image2 from (select id, name, title, administrators, time from factorys " + condition + \
                        ") t1 left join bg_examine t2 on array_to_string(t1.administrators, ',', '*') = t2.id) t;"
            cur.execute(sql_count)
            total = cur.fetchone()[0] or 0

            sql = "select * from (select row_number() over (order by t1.time desc) as rn, t1.id, t1.name, t1.title," \
                  " t1.administrators, t2.industry, t2.region, t2.image1, t2.image2 from (select id, name, title," \
                  " administrators, time from factorys " + condition + ") t1 left join bg_examine t2  on " \
                                                                       " array_to_string(t1.administrators, ',', '*') = t2.id) t where rn > %d limit %d;" % (
                      offset, row)
            # print(sql)
            cur.execute(sql)
            result = cur.fetchall()

            data = []
            for res in result:
                di = dict()
                di["rn"] = res[0]
                di["factory_id"] = res[1]
                di["contact"] = res[2] or ""
                di["company_name"] = res[3] or ""
                di["administrators"] = res[4] or ""
                di["company_category"] = res[5] or ""
                di["company_area"] = res[6] or ""
                di["auth_file"] = alioss.joint_image(res[7]) if res[7] else ""
                di["business_licence"] = alioss.joint_image(res[8]) if res[8] else ""
                cur.execute(
                    "select count(phone) from factory_users where rights != '{1}' and factory = '%s';" % di[
                        "factory_id"])
                di["normal_admin"] = cur.fetchone()[0] or 0
                data.append(di)
            return Response({"total": total, "data": data}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)


class FactoryNew(APIView):
    """创建新企业用户 /facs/new"""

    def post(self, request):
        company_name = request.data.get("company_name")  # 公司名称
        contact = request.data.get("contact")  # 联系人
        administrators = request.data.get("administrators")  # 超级管理员手机号
        company_area = request.data.get("company_area", "")  # 公司地区
        company_category = request.data.get("company_category", "")  # 公司类别
        auth_file = request.data.get("auth_file", "")  # 授权文件
        business_licence = request.data.get("business_licence", "")  # 营业执照
        # print(company_name, contact, administrators, company_area, company_category, auth_file[:20],
        #       business_licence[:20])
        if not all([company_name, contact, administrators]):
            return Response({"res": 1, "errmsg": "缺少参数！"}, status=status.HTTP_200_OK)
        if not re.match("^(13[0-9]|14[579]|15[0-3,5-9]|16[6]|17[0135678]|18[0-9]|19[89])\\d{8}$", administrators):
            return Response({"res": 1, "errmsg": "手机号格式错误！"}, status=status.HTTP_200_OK)

        id = generate_uuid()
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        alioss = AliOss()

        admin_check = "select count(1) from factorys where administrators = '{%s}';" % administrators
        cur.execute(admin_check)
        result_admin_chenck = cur.fetchone()[0]
        # print("result_admin_chenck=", result_admin_chenck)
        if result_admin_chenck >= 1:
            return Response({"res": 1, "errmsg": "电话号码已存在于其它工厂！"}, status=status.HTTP_200_OK)

        phone_check = "select count(1) from factory_users where phone = '%s';" % administrators
        cur.execute(phone_check)
        result_phone_check = cur.fetchone()[0]
        # print("result_phone_check=", result_phone_check)
        if result_phone_check >= 1:
            return Response({"res": 1, "errmsg": "电话号码已存在于其它工厂!"}, status=status.HTTP_200_OK)

        company_name_sql = "select count(1) from factorys where title = '%s';" % company_name
        cur.execute(company_name_sql)
        company_name_check = cur.fetchone()[0]
        if company_name_check >= 1:
            return Response({"res": 1, "errmsg": "公司名称已存在！"}, status=status.HTTP_200_OK)

        timestamp = int(time.time())
        try:
            sql = "insert into factorys (id, name, title, administrators, time) values (" + "'%s', '%s', '%s', '{%s}', %d" % (
                id, contact, company_name, administrators,
                timestamp) + ") on CONFLICT (id) do update set name = '%s', title = '%s', administrators = '{%s}', time = %d;" % (
                      contact, company_name, administrators, timestamp)
            # print(sql)
            cur.execute(sql)
            user_sql = "insert into factory_users (phone, rights, factory, time) values (%s, '{1}', '%s', %d);" % (
                administrators, id, timestamp)
            # print(user_sql)
            cur.execute(user_sql)

            auth_file_id, auth_file_url = alioss.upload_image(auth_file)
            business_licence_id, business_licence_url = alioss.upload_image(business_licence)
            auth_file_id, auth_file_url = (auth_file_id, auth_file_url) if auth_file else ("", "")
            business_licence_id, business_licence_url = (
                business_licence_id, business_licence_url) if business_licence else ("", "")
            # print("auth_file_id", auth_file_id, "auth_file_url", auth_file_url)
            # print("business_licence_id", business_licence_id, "business_licence_url", business_licence_url)

            bg_examine_sql = "insert into bg_examine (id, name, industry, region, contact, image1, image2, time)" \
                             " values ('%s', '%s', '%s', '%s', '%s', '%s', '%s', %d);" % (administrators,
                                                                                          company_name,
                                                                                          company_category,
                                                                                          company_area, administrators,
                                                                                          auth_file_id,
                                                                                          business_licence_id,
                                                                                          timestamp)
            cur.execute(bg_examine_sql)

            conn.commit()
            return Response({"res": 0}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)


class FactoryDelete(APIView):
    """删除企业用户 /facs/del"""

    def delete(self, request):
        id = request.data.get("id")  # 企业唯一ID
        if not id:
            return Response({"res": 1, "errmsg": "缺少工厂id！"}, status=status.HTTP_200_OK)
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        cur.execute("select count(id) from factorys where id = '%s';" % id)
        id_check = cur.fetchone()[0]
        # print("id_check=", id_check)
        if id_check == 0:
            return Response({"res": 1, "errmsg": "id不存在，无法删除!"}, status=status.HTTP_200_OK)

        try:
            cur.execute("select administrators from factorys where id = '%s';" % id)
            result_administrators = cur.fetchone()[0]
            # print(result_administrators, type(result_administrators))  # list
            for res in result_administrators:
                cur.execute("delete from bg_examine where id = '%s';" % res)

            cur.execute("delete from factorys where id = '%s';" % id)
            cur.execute("delete from user_tp_apps where factory_id = '%s';" % id)
            cur.execute("delete from tp_apps_order where factory_id = '%s';" % id)
            cur.execute("delete from factory_users where factory = '%s';" % id)
            conn.commit()
            return Response({"res": 0}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)


class FactoryModify(APIView):
    """修改企业用户信息 bg/facs/modify"""

    def put(self, request):
        factory_id = request.data.get("factory_id")  # 企业唯一ID
        company_name = request.data.get("company_name")  # 公司名称
        contact = request.data.get("contact")  # 联系人
        administrators = request.data.get("administrators")  # 超级管理员手机号
        company_area = request.data.get("company_area", "")  # 公司地区
        company_category = request.data.get("company_category", "")  # 公司类别
        auth_file = request.data.get("auth_file", "")  # 授权文件
        business_licence = request.data.get("business_licence", "")  # 营业执照
        if not factory_id:
            return Response({"res": 1, "errmsg": "缺少工厂id"}, status=status.HTTP_200_OK)
        if not re.match("^(13[0-9]|14[579]|15[0-3,5-9]|16[6]|17[0135678]|18[0-9]|19[89])\\d{8}$", administrators):
            return Response({"res": 1, "errmsg": "电话号码格式错误"}, status=status.HTTP_200_OK)

        alioss = AliOss()
        rabbitmq = UtilsRabbitmq()
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        try:
            timestamp = int(time.time())
            cur.execute("select count(1) from factorys where id = '%s';" % factory_id)
            id_check = cur.fetchone()[0]
            # print("id_check=", id_check)
            if id_check == 0:
                return Response({"res": 1, "errmsg": "工厂id不存在！"}, status=status.HTTP_200_OK)

            cur.execute("select count(1) from factorys where administrators = '{%s}'" % administrators)
            admin_check = cur.fetchone()[0]
            # admin_check = admin_check[0] if admin_check else 0
            # print("admin_check=", admin_check)
            if admin_check > 1:
                return Response({"res": 1, "errmsg": "管理员手机号已存在！"}, status=status.HTTP_200_OK)

            cur.execute("select count(1) from factory_users where phone = '%s';" % administrators)
            phone_check = cur.fetchone()[0]
            # print(phone_check)
            if phone_check > 1:
                return Response({"res": 1, "errmsg": "管理员手机号已存在！"}, status=status.HTTP_200_OK)

            cur.execute(
                "update factorys set name = '%s', title = '%s', administrators = '{%s}', time = %d where id = '%s';" % (
                    contact, company_name, administrators, timestamp, factory_id))
            cur.execute("delete from factory_users where factory = '%s' and '1' = ANY(rights);" % factory_id)
            cur.execute(
                "insert into factory_users (phone, name, rights, time, factory) values ('%s', '%s', '{1}', %d, '%s');" % (
                    administrators, contact, timestamp, factory_id))

            # 不上传新图片时前端传图片id，上传新图片时传base64转码后内容
            if auth_file:
                if len(auth_file) == 18:
                    auth_file_id = auth_file
                else:
                    auth_file_id, auth_file_url = alioss.upload_image(auth_file)
            else:
                auth_file_id = ""

            if business_licence:
                if len(business_licence) == 18:
                    business_licence_id = business_licence
                else:
                    business_licence_id, business_licence_url = alioss.upload_image(business_licence)
            else:
                business_licence_id = ""
            # print(auth_file_id, business_licence_id)
            cur.execute("select phone from user_info where name = '%s';" % contact)
            temp = cur.fetchone()
            # print("temp=", temp)
            contact_phone = temp[0] if temp else administrators
            # print("contact_phone=", contact_phone)
            cur.execute(
                "update bg_examine set name = '%s', industry = '%s', region = '%s', contact = '%s', image1 = '%s',"
                " image2 = '%s', time = %d  where id = '%s';" % (
                    company_name, company_category, company_area, contact_phone, auth_file_id,
                    business_licence_id, timestamp, administrators))

            conn.commit()
            message = {'resource': 'BgFacsModify', 'type': 'POST',
                       'params': {'id': factory_id, 'name': contact, 'title': company_name,
                                  'administrators': administrators}}
            try:
                rabbitmq.send_message(json.dumps(message))
            except Exception as e:
                logger.error(e)

            return Response({"res": 0}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)


class BgAdmins(APIView):
    """管理员 /bg/facs/admins"""

    def get(self, request):
        """管理员列表查询"""
        factory_id = request.query_params.get("factory_id")
        username = request.query_params.get("username")
        phone = request.query_params.get("phone")
        row = int(request.query_params.get("row", 10))  # 每页数量(默认值为10)
        page = int(request.query_params.get("page", 1))  # 当前页数(默认值为1)
        offset = row * (page - 1)
        if not factory_id:
            return Response({"res": 1, "errmsg": "缺少工厂id！"}, status=status.HTTP_200_OK)

        condition_phone = ""
        condition_username = ""
        count_phone = ""
        count_username = ""
        if not username and not phone:
            condition_phone += ""
            condition_username += " where"
            count_phone += ""
            count_username += ""
        elif username and not phone:
            condition_phone += ""
            condition_username += " where name like '%" + username + "%' and"
            count_phone += ""
            count_username += "where name like '%" + username + "%'"
        elif phone and not username:
            condition_phone += " and phone like '%" + phone + "%'"
            condition_username += "where"
            count_phone += " and phone like '%" + phone + "%'"
            count_username += ""
        elif username and phone:
            condition_phone += " and phone like '%" + phone + "%'"
            condition_username += " where name like '%" + username + "%' and"
            count_phone += " and phone like '%" + phone + "%'"
            count_username += " where name like '%" + username + "%'"
        # print(condition)
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        alioss = AliOss()

        try:
            sql_count = "select count(1) from (select row_number() over (order by t3.row_time desc) as rn, t3.phone, t3.rights, t3.factory, t3.title, t3.administrators, t4.name, t4.image from (select * from (select phone, rights, time as row_time, factory from factory_users where factory = '%s' and rights != '{1}'" % factory_id + count_phone + ") t1 left join factorys t2 on t1.factory = t2.id) t3 left join user_info t4 on t3.phone = t4.phone) t " + count_username + ";"
            # print(sql_count)
            cur.execute(sql_count)
            total = cur.fetchone()[0] or 0

            sql = "select * from (select row_number() over (order by t3.row_time desc) as rn, t3.phone, t3.rights, t3.factory, t3.title, t3.administrators, t4.name, t4.image from (select * from (select phone, rights, time as row_time, factory from factory_users where factory = '%s' and rights != '{1}'" % factory_id + condition_phone + ") t1 left join factorys t2 on t1.factory = t2.id) t3 left join user_info t4 on t3.phone = t4.phone) t " + condition_username + " rn > %d limit %d;" % (
                offset, row)

            # print(sql)
            cur.execute(sql)
            result = cur.fetchall()
            # print(result)
            data = []
            for res in result:
                di, permission = dict(), list()
                di["rn"] = res[0]
                di["phone"] = res[1] or ""
                # (1, '18086455876', ['3', '4', '5', '7', '9', '9eG4F680s5X6g7SHYm', '9eG7LLNjN7APaPTdKa', '9eG3bKV80wljfhIvDs', '9eG3WMmW6lfbIR4SZ6', '9eG1sCv1G6v3AaKoRE', '9eG52DcRoEAC6I75FY', '9eG3ik0BbJLGmwMhrE', '9eG2PexY1bHBh1T7K4', '9eG1fFexkxwluFe9QW', '9eG3EfAezwZP7LvEky'], '9eaMGka5ddoalaix8a', '深圳市大数点技术运营有限公司', ['18671618611'], '朱鹤', <memory at 0x7f8a205267c8>)
                permission_list = res[2]
                for per in permission_list:
                    if len(per) == 1 and per in RIGHTS_DICT:
                        per = RIGHTS_DICT[per]
                        permission.append(per)
                    # else:
                    #     cur.execute("select name from tp_apps where id = '%s';" % per)
                    #     per = cur.fetchone()
                    #     per = per[0] if per else ""

                di["permission"] = permission
                di["factory_id"] = res[3] or ""
                di["company"] = res[4] or ""
                administrators = res[5] or ""
                # print(administrators)
                di["role"] = "普通管理员" if res[1] not in administrators else "超级管理员"
                di["username"] = res[6] or ""
                image = res[7] if res[7] else None
                avatar = ""
                if isinstance(image, str):
                    avatar = alioss.joint_image(image)
                elif isinstance(image, memoryview):
                    avatar = alioss.joint_image(image.tobytes().decode())
                # print("image=", image, "avatar=", avatar)
                di["avatar"] = avatar
                data.append(di)
            # print(data)
            return Response({"permission": EDIT_RIGHTS_LIST, "total": total, "data": data}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)

    def post(self, request):
        """新增普通管理员"""
        factory_id = request.data.get("factory_id")
        company_name = request.data.get("company_name")  # 所属公司
        new_administrators = request.data.get("new_administrators")  # 超级管理员手机号
        permission = request.data.get("permission")  # 拥有权限
        # print("administrators=", administrators, type(administrators))
        # print("permission=", permission, type(permission))  # ['1', '4'] <class 'list'>
        if not all([factory_id, new_administrators, permission]):
            return Response({"res": 1, "errmsg": "缺少参数！"}, status=status.HTTP_200_OK)
        if not re.match("^(13[0-9]|14[579]|15[0-3,5-9]|16[6]|17[0135678]|18[0-9]|19[89])\\d{8}$", new_administrators):
            return Response({"res": 1, "errmsg": "电话号码格式错误！"}, status=status.HTTP_200_OK)

        permission = list(set(permission))
        permission = ','.join(permission)
        # print("permission=", permission, type(permission))
        timestamp = int(time.time())
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        try:
            cur.execute("select count(1) from factory_users where phone = '%s';" % new_administrators)
            phone_check = cur.fetchone()[0]
            # print(phone_check)
            if phone_check == 1:
                return Response({"res": 1, "errmsg": "电话号码已存在！"}, status=status.HTTP_200_OK)

            cur.execute("select name from user_info where phone = '%s';" % new_administrators)
            name = cur.fetchone()
            name = name[0] if name else ""
            cur.execute(
                "insert into factory_users (phone, name, rights, time, factory) values ('%s', '%s', '{%s}', %d, '%s');" % (
                    new_administrators, name, permission, timestamp, factory_id))
            conn.commit()
            return Response({"res": 0}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)

    def put(self, request):
        """修改普通管理员"""
        factory_id = request.data.get("factory_id")  # 公司唯一id
        administrators = request.data.get("administrators")  # 旧的超级管理员手机号
        new_administrators = request.data.get("new_administrators")  # 新的超级管理员手机号
        permission = request.data.get("permission")  # 拥有权限

        if not all([factory_id, administrators, permission, new_administrators]):
            return Response({"res": 1, "errmsg": "缺少参数！"}, status=status.HTTP_200_OK)

        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        try:
            permission = list(set(permission))
            permission = ','.join(permission)
            timestamp = int(time.time())
            cur.execute("select name from user_info where phone = '%s';" % administrators)
            name = cur.fetchone()
            name = name[0] if name else ""
            # print("name=", name)

            cur.execute(
                "delete from factory_users where factory = '%s' and phone = '%s';" % (factory_id, administrators))
            cur.execute(
                "insert into factory_users (phone, name, rights, time, factory) values ('%s', '%s', '{%s}', %d, '%s');" % (
                    new_administrators, name, permission, timestamp, factory_id))

            conn.commit()
            return Response({"res": 0}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)


class BgAdminsDelete(APIView):
    """删除普通管理员 /bg/facs/del"""

    def delete(self, request, factory_id, administrators):
        """
        :param factory_id: 企业唯一ID
        :param administrators: 普通管理员手机号
        """

        # print(factory_id, administrators)
        if not all([factory_id, administrators]):
            return Response({"res": 1, "errmsg": "缺少工厂id！"}, status=status.HTTP_200_OK)
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        try:
            cur.execute("select phone from factory_users where factory = '%s';" % factory_id)
            temp = cur.fetchall()
            # print(temp, len(temp))
            phone_check = []
            for ph in temp:
                phone_check.append(ph[0])
            # print(phone_check)
            if administrators not in phone_check:
                return Response({"res": 1, "errmsg": "电话号码不存在，无法删除！"}, status=status.HTTP_200_OK)

            cur.execute(
                "delete from factory_users where factory = '%s' and phone = '%s';" % (factory_id, administrators))
            conn.commit()
            return Response({"res": 0}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)
