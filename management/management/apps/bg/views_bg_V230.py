import base64
import datetime
import logging
import time
import re
import jwt
import json

from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps_utils import UtilsRabbitmq, UtilsPostgresql
from bg.utils import generate_password, generate_uuid
from bg.utils import AliOss

logger = logging.getLogger('django')


# V2.3.0----------------------------------------------------------------------------------------------------------------


class Password(APIView):
    """生成密码"""

    def get(self, request):
        password = request.query_params.get("password")
        ge_password = generate_password(password)
        return Response(ge_password, status=status.HTTP_200_OK)


class ImageTest(APIView):
    """图片功能测试"""

    def get(self, request):
        image_id = request.query_params.get("image_id")
        alioss = AliOss()
        image_list = alioss.list_images(10)
        image_url = alioss.joint_image(image_id)
        print(image_list)
        return Response(image_url)

    def post(self, request):
        image = request.data.get("image")
        # print(type(image), image.__class__)

        alioss = AliOss()
        image_id, image_url = alioss.upload_image(image)
        return Response("%s %s" % (image_id, image_url))


class Login(APIView):
    """后台管理登录"""

    def get(self, request):
        authorization = request.META.get("HTTP_AUTHORIZATION")
        # authorization = request.META["HTTP_AUTHORIZATION"]
        # print(request.META)
        # print(authorization, type(authorization))
        if not authorization:
            return Response({"res": 1, "errmsg": "你未认证无法登录！"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            authorization = authorization.split(" ")[-1]
            # print(authorization)
            info = base64.b64decode(authorization).decode()
            # print(info)  # test:test
        except Exception:
            return Response({"res": 1, "errmsg": "请求头token错误！"}, status=status.HTTP_200_OK)   
        else:
            login_username = info.split(":")[0]  # 'test'
            login_password = info.split(":")[-1]  # 'test'
            # print(login_username, login_password)
            logger.info(login_username, login_password)

            postgresql = UtilsPostgresql()
            conn, cur = postgresql.connect_postgresql()

            try:
                # 判断是手机号还是用户名
                if login_username.isdigit() and len(login_username) == 11:
                    login_type = 'phone'
                else:
                    login_type = 'username'
                cur.execute("select rights from bg_user where %s='%s';" % (login_type, login_username))
                res = cur.fetchone()
                # print("res=", res)
                if not res:
                    return Response({"errmsg": "%s不存在！" % login_type}, status=status.HTTP_200_OK)
                cur.execute("select count(1) from bg_user where %s='%s' and password = crypt('%s', password);"
                            % (login_type, login_username, login_password))
                verify_boolean = cur.fetchone()[0]
                # print("verify_boolean=", verify_boolean)
                if verify_boolean:
                    payload = {"username": login_username, "exp": datetime.datetime.utcnow() + datetime.timedelta(
                        days=7)}
                    jwt_token = jwt.encode(payload, settings.SECRET_KEY)
                    # print("jwt_token=", jwt_token)
                    responses = {
                        "res": 0,
                        "jwt": jwt_token,
                        "right": int(res[0])
                    }
                    return Response(responses, status=status.HTTP_200_OK)
                else:
                    responses = {
                        "res": 1,
                        "errmsg": "密码校验失败！"
                    }
                    return Response(responses, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(e)
                return Response({"res": 1, "errmsg": "服务器错误！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            finally:
                postgresql.disconnect_postgresql(conn)


class BgList(APIView):
    """后台认证列表 /bg/list"""

    def get(self, request, *args, **kwargs):
        id = request.query_params.get("id", "")  # 手机号
        username = request.query_params.get("username", "")  # 用户名
        name = request.query_params.get("name", "")  # 名字
        country = request.query_params.get("country", "")  # 国家
        start = request.query_params.get("start")  # 开始时间
        endt = request.query_params.get("endt")  # 结束时间
        page = request.query_params.get("page", 1)  # 当前页数
        row = request.query_params.get("row", 10)  # 每页数量
        row = 10 if int(row) < 10 else int(row)
        RN = (int(page) - 1) * row
        auth_state = request.query_params.get("state")  # 增加搜索条件：用户的身份认证状态

        if auth_state:
            if auth_state not in ["1", "2", "3"]:
                return Response({"res": 1, "errmsg": "认证状态代号错误！"}, status=status.HTTP_200_OK)

        country = " and country = '" + country + "' " if country else ""
        start = " and time >= " + start if start else ""
        endt = " and time <= " + endt if endt else ""
        # print("id=", id, "username=", username, "name=", name, "country=", country, start, endt, row, RN, auth_state)

        condition = ""
        if username and not auth_state:
            condition += " where t2.name like '%" + username + "%'"
        elif auth_state and not username:
            condition += " where t2.auth_state = " + auth_state
        elif username and auth_state:
            condition += " where t2.name like '%" + username + "%' and t2.auth_state = " + auth_state
        # print("condition=", condition)

        sql = "select * from (select t1.phone, t2.name as username, t1.type, t1.name, t1.country, t1.time, t1.image1," \
              " t1.image2, t1.image3, t2.auth_state as state, t1.auth_msg as msg, row_number() over" \
              " (order by t1.time desc) as rn from (select * from user_auth where phone like '%" + id + \
              "%' and name like '%" + name + "%' " + start + endt + country + ") t1 left join user_info t2 " \
              " on t1.phone = t2.phone" + condition + ") t where rn > {} order by rn asc limit {};".format(RN, row)

        # print(sql)
        sql_count = "select count(1) from (select t1.phone, t2.name as username, t1.type, t1.name, t1.country, " \
                    "t1.time, t1.image1, t1.image2, t1.image3, t2.auth_state as state, t1.auth_msg as msg from " \
                    "(select * from user_auth where phone like '%" + id + "%' and name like '%" + name + "%' " + \
                    start + endt + country + ") t1 left join user_info t2 on t1.phone = t2.phone" + condition + ") t ;"
        # print(sql_count)
        alioss = AliOss()
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        try:
            data = []
            cur.execute(sql_count)
            total = cur.fetchone()[0] or 0

            cur.execute(sql)
            result = cur.fetchall()
            # print("result=", result)
            for res in result:
                di = dict()
                di["id"] = res[0] or ""
                di["username"] = res[1] or ""
                di["type"] = res[2] or ""
                di["name"] = res[3] or ""
                di["country"] = res[4] or ""
                di["time"] = res[5] or None
                if isinstance(res[6], memoryview):
                    memory1 = res[6].tobytes().decode()
                    di["image1"] = alioss.joint_image(memory1)
                else:
                    di["image1"] = ""

                if isinstance(res[7], memoryview):
                    memory2 = res[7].tobytes().decode()
                    di["image2"] = alioss.joint_image(memory2)
                else:
                    di["image2"] = ""

                if isinstance(res[8], memoryview):
                    memory3 = res[8].tobytes().decode()
                    di["image3"] = alioss.joint_image(memory3)
                else:
                    di["image3"] = ""

                di["state"] = res[9] if res[9] else None
                data.append(di)
            # print("data=", data)
            postgresql.disconnect_postgresql(conn)
            return Response({"data": data, "total": total}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"res": 1, "errmsg": "服务器错误！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Auth(APIView):
    """审核 /bg/auth
    user_info.auth_state = 0    数据表字段的默认值
    user_info.auth_state = 1    未认证
    user_info.auth_state = 2    认证未通过
    user_info.auth_state = 3    认证通过
    """

    def post(self, request):
        id = request.data.get("id")  # 唯一ID "13602590001"
        state = request.data.get("state")  # 审核状态 "2"
        msg = request.data.get("msg") or "认证未通过"  # 审核不通过原因 "测试"
        rabbitmq = UtilsRabbitmq()
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        if not id:
            return Response({"res": 1, "errmsg": "缺少id"}, status=status.HTTP_200_OK)
        elif state not in ["0", "2", "3"]:
            return Response({"res": 1, "errmsg": "认证状态码错误"}, status=status.HTTP_200_OK)

        cur.execute("select count(phone) from user_info where phone = '%s';" % id)
        id_check = cur.fetchone()[0]
        if id_check == 0:
            return Response({"res": 1, "errmsg": "该用户不存在"}, status=status.HTTP_200_OK)
        try:
            # print("state=", state, type(state))  # state= 2 <class 'str'>
            if state == "2":
                cur.execute("update user_info set auth_state = 2 where phone = '%s';" % id)
                cur.execute("update user_auth set auth_msg = '%s' where phone = '%s';" % (msg, id))
            elif state == "3":
                cur.execute("update user_info set auth_state = 3 where phone = '%s';" % id)
                cur.execute("update user_auth set auth_msg = '认证通过' where phone = '%s';" % id)
            conn.commit()
            message = {'resource': 'BgAuth', 'type': 'POST', 'params': {'id': id, 'state': state, 'msg': msg}}
            rabbitmq.send_message(json.dumps(message))
            return Response({"res": 0}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器错误！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)


class File(APIView):
    """下载图片 /bg/file
    不需要校验token"""

    def get(self, request):
        id = request.query_params.get("id")  # 图片唯一id
        if not id:
            return Response({"res": 1, "errmsg": "缺少id"}, status=status.HTTP_200_OK)
        try:
            alioss = AliOss()
            image = alioss.joint_image(id)
            return HttpResponse(image, content_type="image/jpg", status=status.HTTP_200_OK)
        except Exception:
            return Response({"res": 1, "errmsg": "图片不存在"}, status=status.HTTP_200_OK)


class FactoryNames(APIView):
    """后台企业名称列表 /bg/facs/names"""

    def get(self, request):
        data = []
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        try:
            cur.execute("select id, name from factorys order by time desc;")
            result_factorys = cur.fetchall()
            # print("result_factorys=", result_factorys)
            # print(len(result_factorys))
            for res in result_factorys:
                di = dict()
                di["id"] = res[0] or ""  # 唯一ID
                di["name"] = res[1] or ""  # 企业名称
                data.append(di)
            return Response({"res": 0, "data": data}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器错误！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)


class UserList(APIView):
    """后台认证列表 /bg/user/list"""

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        Id = request.GET.get('id', '')
        name = request.GET.get('name', '')
        factory_id = request.GET.get('factory_id')

        row = request.GET.get('row', 10)
        page = request.GET.get('page', 1)

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        sdsd = request.GET.get('sdsd')
        edsd = request.GET.get('edsd')
        stime = request.GET.get('stime', '0')
        etime = request.GET.get('etime')
        if etime is not None:
            p_1 = " time >= %s and time <= %s and" % (stime, etime)
        else:
            p_1 = " time >= %s and" % stime
        if sdsd and edsd:
            p_2 = " coin >= %s and coin <= %s " % (sdsd, edsd)
        elif sdsd:
            p_2 = " coin >= %s " % sdsd
        elif edsd:
            p_2 = " coin <= %s " % edsd
        else:
            p_2 = ''

        part_sql = (p_1 + p_2).rstrip('and')
        part_sql = 'and' + part_sql if part_sql else ''

        sql = "select * from (select t1.phone, t1.name, t1.image, t1.coin as dsd_val, t1.auth_state as state, t1.time" \
              ", COALESCE(t3.title, '') as factory, row_number() over (order by t1.time desc) as rn from (select * " \
              "from user_info where phone like '%" + Id + "%' and name like '%" + name + "%' " + part_sql \
              + " ) t1 left join factory_users t2 on t1.phone = t2.phone left join (select * from factorys) t3 on " \
                "t2.factory = t3.id " + ("where t3.id = '%s'" % factory_id if factory_id else '') + ")t where rn > %d " \
              % offset + "order by rn asc limit %d;" % limit
        # print(sql)
        sql_count = "select count(1) from (select * from user_info where phone like '%" + Id + \
                    "%' and name like '%" + name + "%' " + part_sql + \
                    ")t1 left join factory_users t2 on t1.phone = t2.phone left join (select * from factorys)t3 on " \
                    "t2.factory = t3.id " + ("where t3.id = '%s';" % factory_id if factory_id else ';')

        target = ['phone', 'name', 'image', 'dsd_val', 'state', 'time', 'factory', 'rn']

        try:
            cur.execute(sql)
            tmp = cur.fetchall()
            cur.execute(sql_count)
            total = cur.fetchone()[0]
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # data
        alioss = AliOss()
        data = []
        for i in tmp:
            t = dict(zip(target, i))
            if isinstance(t['image'], memoryview):
                t['image'] = t['image'].tobytes().decode()
            t['image'] = alioss.joint_image(t['image'])
            data.append(t)

        result = dict()
        result['total'] = total if total else 0
        result['data'] = data

        postgresql.disconnect_postgresql(conn)
        return Response(result, status=status.HTTP_200_OK)


class UserStatus(APIView):
    """用户统计信息 /bg/user/stats"""

    def get(self, request):
        # total_users, active_users, new_users, active_rate,
        weekago_timestamp = time.mktime(
            time.localtime(time.mktime(time.strptime(time.strftime("%Y-%m-%d"), '%Y-%m-%d')) - 6 * 86400))
        today_timestamp = time.mktime(time.strptime(time.strftime("%Y-%m-%d"), '%Y-%m-%d'))

        sql = "select (select count(phone) from user_info) as total_users , (select count(phone) from user_info where" \
              " time > %f) as new_users , count(phone) as active_users from user_activity_log where time > %f;" \
              % (today_timestamp, weekago_timestamp)

        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        try:
            cur.execute(sql)
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        tmp = cur.fetchone()

        total_users, new_users, active_users = tmp
        if total_users is None:
            total_users = 0
        if new_users is None:
            new_users = 0
        if active_users is None:
            active_users = 0
        active_rate = round(active_users / total_users * 100, 2) if total_users else 0

        # new_user_stats
        new_user_stats = []
        tendays_timestamp = time.mktime(
            time.localtime(time.mktime(time.strptime(time.strftime("%Y-%m-%d"), '%Y-%m-%d')) - 9 * 86400))

        sql = "select to_char(to_timestamp(time), 'YYYY-MM-DD') as date, count(phone) from user_info " \
              "where time > %f group by date order by date desc;" % tendays_timestamp
        try:
            cur.execute(sql)
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        tmp = cur.fetchall()

        dates = (time.strftime("%Y-%m-%d", time.localtime(
            time.mktime(time.strptime(time.strftime("%Y-%m-%d"), '%Y-%m-%d')) - i * 86400)) for i in range(10))
        date_num = dict(tmp)
        for i in dates:
            if i in date_num:
                new_user_stats.append({'date': i, 'num': date_num[i]})
            else:
                new_user_stats.append({'date': i, 'num': 0})

        # active_users_status
        active_users_status = []
        tendays_timestamp = int(round(time.time())) - 10 * 86400
        sql = "select to_char(to_timestamp(time), 'YYYY-MM-DD') as date, COALESCE(count(phone),0) from user_activity" \
              "_log where time > %d group by date order by date desc;" % tendays_timestamp

        try:
            cur.execute(sql)
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        tmp = cur.fetchall()

        dates = (time.strftime("%Y-%m-%d", time.localtime(
            time.mktime(time.strptime(time.strftime("%Y-%m-%d"), '%Y-%m-%d')) - i * 86400)) for i in range(10))
        date_num = dict(tmp)
        for i in dates:
            if i in date_num:
                active_users_status.append({'date': i, 'num': date_num[i]})
            else:
                active_users_status.append({'date': i, 'num': 0})
        # 这部分数据还是不确定
        new_user_city_stats = []
        active_users_city_stats = []

        postgresql.disconnect_postgresql(conn)

        result = dict()
        result['total_users'] = total_users
        result['active_users'] = active_users
        result['new_users'] = new_users
        result['active_rate'] = active_rate
        result['new_user_stats'] = new_user_stats
        result['active_users_status'] = active_users_status
        result['new_user_city_stats'] = new_user_city_stats
        result['active_users_city_stats'] = active_users_city_stats
        return Response(result, status=status.HTTP_200_OK)


class DsdGrant(APIView):
    """系统赠送DSD /bg/dsd/grant"""

    def post(self, request):
        rabbitmq = UtilsRabbitmq()
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        now = int(time.time())
        phone = request.data.get('id', '')
        dsd = request.data.get('dsd_val', '')

        # check
        try:
            dsd = float(dsd)
            if not re.match("^(13[0-9]|14[579]|15[0-3,5-9]|16[6]|17[0135678]|18[0-9]|19[89])\\d{8}$", phone):
                return Response({'res': 1, 'errmsg': "手机号码输入格式错误"}, status=status.HTTP_200_OK)
            if dsd <= 0:
                return Response({'res': 1, 'errmsg': "DSD数量格式错误"}, status=status.HTTP_200_OK)
            cur.execute("select count(1) from user_info where phone = '%s';" % phone)
            tmp = cur.fetchone()[0]
            if tmp != 1:
                return Response({'res': 1, 'errmsg': "赠送的账号不存在"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': "服务器异常"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            cur.execute("insert into coin_records(val, from_type, user_id, time) values(%f, '%s', "
                        "'%s', %d);" % (dsd, 'system', phone, now))
            cur.execute("update user_info set coin = coin + {} where phone = '{}'; ".format(dsd, phone))
            conn.commit()
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # 发送消息
        # b'{"resource": "BgDSDGrant", "type": "POST", "params": {"dsd_val": 1.0, "id": "15325670567"}}'
        message = {'resource': 'BgDSDGrant', 'type': 'POST', 'params': {'id': phone, 'dsd_val': dsd}}
        rabbitmq.send_message(json.dumps(message))
        postgresql.disconnect_postgresql(conn)
        return Response({"res": 0}, status=status.HTTP_200_OK)


class DsdList(APIView):
    """dsd记录查询 /bg/dsd/list"""

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        Id = request.GET.get('id', '')
        name = request.GET.get('name', '')
        from_type = request.GET.get('type')
        factory_id = request.GET.get('factory_id')

        row = request.GET.get('row', 10)
        page = request.GET.get('page', 1)

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        sdsd = request.GET.get('sdsd')
        edsd = request.GET.get('edsd')

        if from_type:
            p_1 = " from_type = '%s' and" % from_type
        else:
            p_1 = ''
        if sdsd and edsd:
            p_2 = " val >= %s and val <= %s " % (sdsd, edsd)
        elif sdsd:
            p_2 = " val >= %s " % sdsd
        elif edsd:
            p_2 = " val <= %s " % edsd
        else:
            p_2 = ''
        part_sql_0 = (p_1 + p_2).rstrip('and')
        part_sql_0 = 'and' + part_sql_0 if part_sql_0 else ''

        if name and factory_id:
            part_sql_1 = "where t2.name like '%{}%' and t4.id = '{}' ".format(name, factory_id)
        elif name:
            part_sql_1 = "where t2.name like '%{}%' ".format(name)
        elif factory_id:
            part_sql_1 = "where t4.id = '{}' ".format(factory_id)
        else:
            part_sql_1 = ""

        sql = "select * from(select t2.phone, t2.name, t2.image, t1.val as dsd_val, t1.from_type as type, t1.time," \
              " coalesce( t4.name, '' ) as factory, row_number() over (order by t1.time desc ) as rn from (select *" \
              " from coin_records where user_id like '%" + Id + "%' " \
              + part_sql_0 + ") t1 left join (select * from user_info) t2 on t1.user_id = t2.phone left join factory" \
                             "_users t3 on t2.phone = t3.phone left join (select * from factorys) t4 on " \
                             "t3.factory = t4.id " + part_sql_1 + "order by t1.time desc ) t where rn > %d " % offset \
              + "order by rn asc limit %d;" % limit

        sql_count = "select count(1) from (select * from coin_records where user_id like '%" + Id + "%' " \
                    + part_sql_0 + ") t1 left join factory_users t2 on t1.user_id = t2.phone left join ( select *" \
                                   " from factorys ) t4 on t2.factory = t4.id " + part_sql_1 + ';'

        target = ['phone', 'name', 'image', 'dsd_val', 'type', 'time', 'factory', 'rn']

        try:
            cur.execute(sql)
            tmp = cur.fetchall()
            cur.execute(sql_count)
            total = cur.fetchone()[0]
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # data
        alioss = AliOss()
        data = []
        for i in tmp:
            t = dict(zip(target, i))
            if isinstance(t['image'], memoryview):
                t['image'] = t['image'].tobytes().decode()
            t['image'] = alioss.joint_image(t['image'])
            data.append(t)

        result = dict()
        result['total'] = total if total else 0
        result['data'] = data

        postgresql.disconnect_postgresql(conn)
        return Response(result, status=status.HTTP_200_OK)


class FeedBackResp(APIView):
    """回复用户反馈 /bg/feedback/resp"""

    def post(self, request):
        rabbitmq = UtilsRabbitmq()
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        id = request.data.get('id')
        msg = request.data.get('msg', '')
        if not id:
            # 手机号非纯数字
            return Response({'msg': "手机号不能为空！"}, status=status.HTTP_200_OK)
        if not msg:
            return Response({'msg': "消息不能为空！"}, status=status.HTTP_200_OK)

        try:
            # gf'分隔符"fh蝶粉蜂黄
            msg = msg.replace("'", "''")
            # msg = msg.replace("\'", "\\\'")
            # msg = msg.replace("\"", "\\\"")
            # print("msg=", msg)
            sql = "update user_feedback set resp = '%s' where id = '%s';" % (msg, id)
            # print(sql)
            cur.execute(sql)
            conn.commit()
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            msg = msg.replace("\\\'", "\'")
            msg = msg.replace("\\\"", "\"")
            # print("msg=", msg)
            message = {'resource': 'BgFeedbackResp', 'type': 'POST', 'params': {'id': id, 'msg': msg}}
            rabbitmq.send_message(json.dumps(message))
        except Exception as e:
            logger.error(e)

        postgresql.disconnect_postgresql(conn)
        return Response({"res": 0}, status=status.HTTP_200_OK)


class FeedbackList(APIView):
    """反馈记录查询 /bg/feedback/list"""

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        Id = request.GET.get('id', '')
        name = request.GET.get('name', '')

        row = request.GET.get('row', 10)
        page = request.GET.get('page', 1)

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        stime = request.GET.get('stime') or '0'
        etime = request.GET.get('etime')
        if etime is not None:
            part_sql_1 = "and time >= %s and time <= %s" % (stime, etime)
        else:
            part_sql_1 = "and time >= %s" % stime
        part_sql_2 = "where t2.name like '%{}%'".format(name) if name else ''
        sql = "select * from ( select t1.id, t1.phone, t2.name, t2.image, t1.content, t1.resp, t1.time, t1.model, " \
              "t1.system, t1.operator, t1.images, row_number() over (order by t1.time desc ) as rn from(select * from" \
              " user_feedback where phone like '%{}%' {}) t1 left join user_info t2 on t1.phone = t2.phone {})t " \
              "where rn > {} order by rn asc limit {};".format(Id, part_sql_1, part_sql_2, offset, limit)

        sql_count = "select count(1) from (select * from user_feedback where phone like '%" + Id + "%' " + part_sql_1 + \
                    ") t1 left join user_info t2 on t1.phone = t2.phone " + (
                        " where t2.name like '%{}%';".format(name) if name else ';')
        target = ['id', 'phone', 'name', 'image', 'content', 'resp', 'time', 'model', 'system', 'operator', 'images', 'rn']
        try:
            cur.execute(sql)
            tmp = cur.fetchall()
            cur.execute(sql_count)
            total = cur.fetchone()[0]
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # data
        alioss = AliOss()
        data = []
        for i in tmp:
            t = dict(zip(target, i))
            if isinstance(t['image'], memoryview):
                t['image'] = t['image'].tobytes().decode()
            t['image'] = alioss.joint_image(t['image'])
            t['images'] = [alioss.joint_image(i.tobytes().decode()) if isinstance(t['image'], memoryview)
                           else alioss.joint_image(i) for i in t['images']]
            data.append(t)

        result = dict()
        result['data'] = data
        result['total'] = total if total else 0
        postgresql.disconnect_postgresql(conn)
        return Response(result, status=status.HTTP_200_OK)


class ExamineList(APIView):
    """企业申请列表 /bg/examine/list """

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        Id = request.GET.get('id', '')
        username = request.GET.get('username', '')
        name = request.GET.get('name', '')

        row = request.GET.get('row', 10)
        page = request.GET.get('page', 1)

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        stime = request.GET.get('stime') or '0'
        etime = request.GET.get('etime')
        if etime is not None:
            part_sql = "and time >= %s and time <= %s " % (stime, etime)
        else:
            part_sql = "and time >= %s " % stime

        sql = "select * from ( select t1.*, t2.name as username, t2.image as user_image, row_number() over (order by" \
              " t1.time desc ) as rn from(select * from bg_examine where id in (select phone from user_info where name" \
              " like '%" + username + "%' and phone like '%" + Id + "%' )and name like '%" + \
              '%s' % name + "%' " + part_sql + \
              ") t1 left join user_info t2 on t1.id = t2.phone ) t where rn > %d" % offset + \
              " order by rn asc limit %d;" % limit

        sql_count = "select count(1) from bg_examine where id in (select phone from user_info where name like '%" + \
                    username + "%' and phone like '%" + Id + "%' ) and name like '%" + '%s' % name + "%' " \
                    + part_sql + ';'

        target = ['id', 'name', 'industry', 'region', 'contact', 'image1', 'image2', 'state', 'state_msg', 'time',
                  'username', 'user_image', 'rn']
        try:
            cur.execute(sql)
            tmp = cur.fetchall()
            cur.execute(sql_count)
            total = cur.fetchone()[0]
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常'}, status=status.HTTP_200_OK)
        # data
        alioss = AliOss()
        data = []
        for i in tmp:
            t = dict(zip(target, i))
            if isinstance(t['image1'], memoryview):
                t['image1'] = t['image1'].tobytes().decode()
            if isinstance(t['image2'], memoryview):
                t['image2'] = t['image2'].tobytes().decode()
            if isinstance(t['user_image'], memoryview):
                t['user_image'] = t['user_image'].tobytes().decode()
            t['image1'] = alioss.joint_image(t['image1'])
            t['image2'] = alioss.joint_image(t['image2'])
            t['user_image'] = alioss.joint_image(t['user_image'])
            data.append(t)

        result = dict()
        result['total'] = total if total else 0
        result['data'] = data

        postgresql.disconnect_postgresql(conn)
        return Response(result, status=status.HTTP_200_OK)


class ExamineId(APIView):
    """企业申请确认 /bg/examine/{id}"""

    def post(self, request, Id):
        rabbitmq = UtilsRabbitmq()
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        state = int(request.data.get('state'))
        state_msg = request.data.get('state_msg', '')
        # print("state=", state, type(state))  # state= 2 <class 'int'>

        try:
            if state_msg:
                cur.execute(
                    "update bg_examine set state = '%d', state_msg = '%s' where id = '%s';" % (state, state_msg, Id))
            else:
                cur.execute("update bg_examine set state = '%d' where id = '%s';" % (state, Id))
            conn.commit()
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if state == 3:
            now = int(time.time())
            cur.execute("select t1.name, t1.contact, t1.industry, t2.name, t1.region from bg_examine t1 left join "
                        "user_info t2 on t1.contact = t2.phone where id = '%s';" % Id)
            factory_info = cur.fetchone()
            name = factory_info[0] or ''
            phone = factory_info[1] or ''
            industry = factory_info[2] or ''
            contacts = factory_info[3] or ''
            region = factory_info[4] or ''

            uuid = generate_uuid()  # 'q66bGqqcTHxQs8KnY6'
            admins = '{' + Id + '}'
            # uuid, name, Id 插入缓存
            try:
                cur.execute("insert into factorys(id, name, title, administrators, time) values('{uuid}', '{name}'"
                            ", '{name}', '{admins}', {time}) ON CONFLICT (id) do update "
                            "set name = '{name}', title = '{name}', administrators = '{admins}', time = {time}"
                            ";".format(uuid=uuid, name=name, admins=admins, time=now))
                cur.execute("insert into factory_users (phone, rights, factory, time) values ('%s', '%s', '%s', %d)"
                            ";" % (Id, '{1}', uuid, now))
                # 将通过审核的公司添加到企业资源池
                cur.execute("insert into base_clients_pool(name, contacts, phone, industry, create_time, region, "
                            "address) values('{}', '{}', '{}', '{}', {}, '{}', '');".format(name, contacts, phone, industry,
                                                                                            now, region))
                conn.commit()
                # 发送消息
                # b'{"resource": "BgExamine", "type": "POST", "params": {"state": "3", "id": "11111111111",
                # "state_msg": "\\u606d\\u559c\\u901a\\u8fc7"}}'
                message = {'resource': 'BgExamine', 'type': 'POST', 'params': {'id': Id, 'state': state,
                                                                               'state_msg': state_msg}}
                rabbitmq.send_message(json.dumps(message))
            except Exception as e:
                logger.error(e)
                return Response({'res': 1, 'errmsg': '服务器异常'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        postgresql.disconnect_postgresql(conn)
        return Response({"res": 0}, status=status.HTTP_200_OK)
