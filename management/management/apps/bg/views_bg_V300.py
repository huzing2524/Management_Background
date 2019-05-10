# -*- coding: utf-8 -*-
import logging
import time
import json

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps_utils import UtilsPostgresql, UtilsRabbitmq
from bg.utils import AliOss, generate_uuid

logger = logging.getLogger('django')


# V3.0.0----------------------------------------------------------------------------------------------------------------


class BgApps(APIView):
    """新增第三方应用 /bg/apps"""

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        Id = request.query_params.get('id')
        name = request.query_params.get('name')  # request.query_params.get('name')
        # print(name, type(name))

        row = request.GET.get('row', 10)
        page = request.GET.get('page', 1)

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        if Id:
            p_1 = " id = '%s' and" % Id
        else:
            p_1 = ''
        if name:
            p_2 = " name like '%{}%'".format(name)
        else:
            p_2 = ''
        part_sql = (p_1 + p_2).rstrip('and')
        part_sql = 'where' + part_sql if part_sql else ''

        sql = "select * from(select t.*, row_number() over (order by t.name desc ) as rn from tp_apps t " + part_sql \
              + ") t where rn > " + str(offset) + " order by rn asc limit %d;" % limit
        sql_count = "select count(1) from tp_apps t " + part_sql + ";"
        target = ['id', 'name', 'slogan', 'dsd_val', 'url', 'icon', 'descs', 'images', 'state', 'time', 'rn']

        try:
            cur.execute(sql)
            tmp = cur.fetchall()
            cur.execute(sql_count)
            total = cur.fetchall()
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # data
        alioss = AliOss()
        data = []
        for i in tmp:
            t = dict(zip(target, i))
            images = t['images']
            for x, y in enumerate(images):
                if isinstance(y, memoryview):
                    images[x] = y.tobytes()
                images[x] = alioss.joint_image(images[x])
            t['icon'] = alioss.joint_image(t['icon'])
            data.append(t)

        result = dict()
        result['total'] = total[0][0]
        result['list'] = data

        postgresql.disconnect_postgresql(conn)
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request):
        """ 新增第三方应用 /bg/apps"""
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        name = request.data.get('name', '')  # 应用名称
        icon = request.data.get('icon', '')  # icon 图像
        slogan = request.data.get('slogan', '')  # 一句话介绍
        descs = request.data.get('descs')  # 详细介绍 array ["test1", "test2", "test3"]
        images = request.data.get('images')  # app截图 array
        dsd_val = request.data.get('dsd_val')  # 每月需要DSD数量
        url = request.data.get('url')  # 链接
        app_id = generate_uuid()

        alioss = AliOss()
        # 上传应用图标
        if icon:
            icon_id = alioss.upload_image(icon)[0]
            if icon_id is None:
                return Response({'res': 1, 'errmsg': '应用图标上传异常'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        else:
            return Response({'res': 1, 'errmsg': "应用图标不能为空"}, status=status.HTTP_200_OK)
        # 上传app截图
        tmp = []
        for i in images:
            image_id = alioss.upload_image(i)[0]
            if image_id is not None:
                tmp.append(image_id)
            else:
                continue

        now = int(time.time())
        images_id = '{' + ','.join(tmp) + '}'
        descs = '{' + ','.join(descs) + '}'

        sql = "insert into tp_apps (id, name, slogan, dsd_val, url, icon, descs, images, state, time) values('{0}', " \
              "'{1}', '{2}', {3}, '{4}', '{5}', '{6}', '{7}', '{8}', {9})".format(app_id, name, slogan,
                                                                                  dsd_val, url, icon_id,
                                                                                  descs, images_id, '0', now)
        # app_id, name, icon_ic, url 插入缓存
        try:
            cur.execute(sql)
            conn.commit()
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        postgresql.disconnect_postgresql(conn)
        return Response({"res": 0}, status=status.HTTP_200_OK)


class BgAppsModify(APIView):

    def put(self, request, id):
        """修改第三方应用 bg/apps/{id}"""
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        if not id:
            return Response({"res": 1, "errmsg": "缺少id！"}, status=status.HTTP_200_OK)

        name = request.data.get("name")  # 应用名称
        icon = request.data.get("icon")  # icon图像 "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD...
        slogan = request.data.get("slogan")  # 一句话介绍
        descs = request.data.get("descs", "")  # 详细介绍 ["test1", "test2", "test3"]
        images = request.data.get("images", "")  # app截图 ["data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAAAAAAAD", , ,]
        dsd_val = request.data.get("dsd_val")  # 每月需要DSD数量
        url = request.data.get("url")  # 链接
        # print(name, icon, slogan, descs, images, dsd_val, url)
        # print(type(name), type(icon), type(slogan), type(descs), type(images), type(dsd_val), type(url))

        try:
            alioss = AliOss()
            descs_store = ''
            for i, desc in enumerate(descs):
                temp = ', ' if (i < len(descs) - 1) else ''
                descs_store += desc + temp

            sql = "update tp_apps set name = '%s', slogan = '%s', dsd_val = '%f', url = '%s', descs = '{%s}' where id = '%s';" % (
                name, slogan, float(dsd_val), url, descs_store, id)
            # print(sql)
            cur.execute(sql)

            if icon:
                # print(type(icon))
                icon_id, icon_url = alioss.upload_image(icon)
                cur.execute("update tp_apps set icon = '%s' where id = '%s';" % (icon_id, id))
                # print(icon_id, icon_url)

            images_store_str = ""
            for i, image in enumerate(images):
                if image:
                    temp = ','
                    image_id, image_url = alioss.upload_image(image)
                    if image_id and image_url:
                        images_store_str = images_store_str + (image_id + temp)
                    else:
                        images_store_str = images_store_str + (image + temp)
            images_store_str = images_store_str.rstrip(",")
            # print("images_store_str=", images_store_str)
            cur.execute("update tp_apps set images = '{%s}' where id = '%s';" % (images_store_str, id))
            conn.commit()

            return Response({"res": 0}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)


class BgAppsState(APIView):
    """app应用隐藏、显示 /bg/apps/state/{id}
    0: 隐藏, 1: 显示"""

    def put(self, request, id):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        state = request.data.get("state")
        if not id:
            return Response({"res": 1, "errmsg": "缺少id！"}, status=status.HTTP_200_OK)
        if not state:
            return Response({"res": 1, "errmsg": "缺少状态！"}, status=status.HTTP_200_OK)
        if state not in ["0", "1"]:
            return Response({"res": 1, "errmsg": "状态代号错误！"}, status=status.HTTP_200_OK)

        try:
            cur.execute("select count(id) from tp_apps where id = '%s';" % id)
            result = cur.fetchone()[0]
            if result == 0:
                return Response({"res": 1, "errmsg": "id不存在！"}, status=status.HTTP_200_OK)
            cur.execute("update tp_apps set state = '%s' where id = '%s';" % (state, id))
            conn.commit()
            return Response({"res": 0}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)


class MarketList(APIView):
    """智能制造市场部 bg/manufacturing/market/list"""

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        Id = request.query_params.get('id')  # 创建人手机号
        name = request.query_params.get('name')  # 创建人姓名
        company = request.query_params.get('company')  # 所属公司
        row = request.GET.get('row', 10)  # 每页的行数, 默认为10
        page = request.GET.get('page', 1)  # 第几页, 默认为1

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        p_1 = "where creator like '%{}%'".format(Id) if Id else ''
        # p_2 = "where c.name like '%{}%'".format(name) if name else ''
        # p_3 = "where name like '%{}%'".format(company) if company else ''

        if name and company:
            p_2 = "where c.name like '%{}%' and e.name like '%{}%'".format(name, company)
        elif name:
            p_2 = "where c.name like '%{}%'".format(name)
        elif company:
            p_2 = "where e.name like '%{}%'".format(company)
        else:
            p_2 = ''

        sql_0 = "select * from (select a.id, b.name, c.name, d.count, e.name, a.time, row_number() over (order by " \
                "a.time desc ) as rn from(select * from orders {0}) a left join factory_clients b on a.client_id = " \
                "b.id left join user_info c on a.creator = c.phone left join (select order_id, sum(sell_price) as" \
                " count from order_products group by order_id ) d on d.order_id = a.id left join factorys e on " \
                "e.id = a.factory {1}) t where rn > {2} order by rn asc limit {3};".format(p_1, p_2, offset, limit)
        sql_count = "select count(1) from (select * from orders {0}) a left join factory_clients b on a.client_id =" \
                    " b.id left join (select order_id, sum(sell_price) as count from order_products" \
                    " group by order_id ) d on d.order_id = a.id left join factorys e on e.id = a.factory left join" \
                    " user_info c on a.creator = c.phone {1};".format(p_1, p_2)
        target_0 = ['order_id', 'client', 'creator', 'sales', 'company', 'time', 'rn', 'product']

        try:
            cur.execute(sql_0)
            tmp = cur.fetchall()
            cur.execute(sql_count)
            total = cur.fetchall()

            target_1 = ['product_name', 'product_count', 'product_unit']
            for x, y in enumerate(tmp):
                sql_1 = "select name, product_count, unit from order_products a left join products b on product_id =" \
                        " b.id where order_id = '%s';" % y[0]
                cur.execute(sql_1)
                t = cur.fetchall()
                product = []
                for j in t:
                    product.append(dict(zip(target_1, j)))
                tmp[x] = tmp[x] + (product,)
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # data
        data = []
        for i in tmp:
            t = dict(zip(target_0, i))
            t['sales'] = round(t['sales'], 2)
            del (t['order_id'])
            data.append(t)

        result = dict()
        result['total'] = total[0]
        result['data'] = data

        postgresql.disconnect_postgresql(conn)
        return Response(result, status=status.HTTP_200_OK)


class FinanceList(APIView):
    """智能制造财务部 bg/manufacturing/finance/list"""

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        Id = request.query_params.get('id')  # 创建人手机号
        name = request.query_params.get('name')  # 创建人姓名
        company = request.query_params.get('company')  # 所属公司

        row = request.GET.get('row', 10)  # 每页的行数, 默认为10
        page = request.GET.get('page', 1)  # 第几页, 默认为1

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        p_1 = " c.phone like '%{}%' and".format(Id) if Id else ''
        p_2 = " c.name like '%{}%' and".format(name) if name else ''
        p_3 = " d.name like '%{}%'".format(company) if company else ''

        condition = (p_1 + p_2 + p_3).rstrip('and')
        condition = 'where' + condition if condition else ''

        sql_0 = "select id, time, creator_id as creator from finance_output union select id, deliver_time as time," \
                " creator from orders union select id, buy_time as time, creator from purchase"

        sql = "select * from (select a.type, a.count, a.time, b.time, c.name, d.name, row_number() over (order by" \
              " a.time desc ) as rn from finance_logs a left join ({0}) b on b.id = a.use_id left join user_info c" \
              " on c.phone = b.creator left join factorys d on d.id = a.factory {1}) t where rn > {2} order by rn asc" \
              " limit {3};".format(sql_0, condition, offset, limit)
        sql_count = "select count(1) from (select * from finance_logs a left join ({0}) b on b.id = a.use_id left" \
                    " join user_info c on c.phone = b.creator left join factorys d on d.id = a.factory {1}) t;" \
                    "".format(sql_0, condition)
        target = ['category', 'sales', 'use_time', 'create_time', 'creator', 'company', 'rn']

        try:
            cur.execute(sql)
            tmp = cur.fetchall()
            cur.execute(sql_count)
            total = cur.fetchall()
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # data
        data = []
        for i in tmp:
            t = dict(zip(target, i))
            if t['sales'] >= 0:
                t['input_output'] = '收入'
            else:
                t['sales'] = -t['sales']
                t['input_output'] = '支出'
            t['sales'] = round(t['sales'], 2)
            data.append(t)

        result = dict()
        result['total'] = total[0]
        result['data'] = data

        postgresql.disconnect_postgresql(conn)
        return Response(result, status=status.HTTP_200_OK)


class MaterialList(APIView):
    """智能制造采购部 bg/manufacturing/material/list"""

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        Id = request.query_params.get('id')  # 创建人手机号
        name = request.query_params.get('name')  # 创建人姓名
        company = request.query_params.get('company')  # 所属公司

        row = request.GET.get('row', 10)  # 每页的行数, 默认为10
        page = request.GET.get('page', 1)  # 第几页, 默认为1

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        p_1 = " e.phone like '%{}%' and".format(Id) if Id else ''
        p_2 = " a.buyer like '%{}%' and".format(name) if name else ''
        p_3 = " c.name like '%{}%'".format(company) if company else ''

        condition = (p_1 + p_2 + p_3).rstrip('and')
        condition = 'where' + condition if condition else ''

        sql = "select * from(select a.material_count, a.total_price, a.buyer, a.buy_time, a.putin_time, a.time," \
              " b.name, c.name, row_number() over (order by a.time desc) as rn from purchase a left join material_" \
              "types b on b.id = a.material_type_id left join factorys c on a.factory = c.id left join factory_users" \
              " d on a.creator = d.phone left join user_info e on e.name = a.buyer {0})t where rn > {1} order by rn" \
              " asc limit {2};".format(condition, offset, limit)
        sql_count = "select count(1) from(select * from purchase a left join material_types b on b.id" \
                    " = a.material_type_id left join factorys c on a.factory = c.id left join factory_users d on" \
                    " a.creator = d.phone left join user_info e on e.name = a.buyer {0}) t;".format(condition)
        target = ['num', 'sales', 'buyer', 'buy_time', 'putin_time', 'create_time', 'product', 'company', 'rn']

        try:
            cur.execute(sql)
            tmp = cur.fetchall()
            cur.execute(sql_count)
            total = cur.fetchall()
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # data
        data = []
        for i in tmp:
            t = dict(zip(target, i))
            t['sales'] = round(t['sales'], 2)
            t['price'] = t['sales'] / t['num']
            data.append(t)

        result = dict()
        result['total'] = total[0]
        result['data'] = data

        postgresql.disconnect_postgresql(conn)
        return Response(result, status=status.HTTP_200_OK)


class ProductsList(APIView):
    """生产部 制造数据显示 bg/manufacturing/products/list"""

    def get(self, request):
        row = request.query_params.get("row", 10)  # 每页的行数, 默认为10
        page = request.query_params.get("page", 1)  # 第几页, 默认为1
        id = request.query_params.get("id")  # 创建人手机号
        name = request.query_params.get("name")  # 创建人姓名
        company = request.query_params.get("company")  # 所属公司
        RN = (int(page) - 1) * int(row)

        # temp = where t6.phone like '%13%' and t6.name like '%飞%' and t5.title like '%立%'
        id = " t6.phone like '%" + id + "%' and" if id else ""
        name = " t6.name like '%" + name + "%' and" if name else ""
        company = " t5.title like '%" + company + "%'" if company else ""
        condition = (id + name + company).rstrip("and")
        condition = " where " + condition if condition else ''
        # print(condition)
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        try:
            data = []
            sql_count = "select count(*)  from (select row_number() over (order by t5.time desc) as rn, t5.name," \
                        " t5.complete_count, t5.start_time, t5.complete_time, t6.name as username, t6.phone," \
                        " t5.title, t5.time from (select t3.name, t3.complete_count, t3.start_time, t3.complete_time," \
                        " t3.creator, t4.title, t3.time from (select t1.factory, t1.product_id, t1.complete_count," \
                        " t1.start_time, t1.complete_time, t1.creator, t1.time, t2.name from" \
                        " (select * from product_task) t1 left join products t2 on t1.product_id = t2.id) t3" \
                        " left join factorys t4 on t3.factory = t4.id ) t5 left join user_info t6 on" \
                        " t5.creator = t6.phone) t;"
            cur.execute(sql_count)
            total = cur.fetchone()[0] or 0
            # print(total)
            sql = "select *  from (select row_number() over (order by t5.time desc) as rn, t5.name," \
                  " t5.complete_count, t5.start_time, t5.complete_time, t6.name as username, t6.phone, t5.title," \
                  " t5.time from (select t3.name, t3.complete_count, t3.start_time, t3.complete_time, t3.creator," \
                  " t4.title, t3.time from (select t1.factory, t1.product_id, t1.complete_count, t1.start_time," \
                  " t1.complete_time, t1.creator, t1.time, t2.name from (select * from product_task) t1 left join" \
                  " products t2 on t1.product_id = t2.id) t3 left join factorys t4 on t3.factory = t4.id ) t5" \
                  " left join user_info t6 on t5.creator = t6.phone" + condition + ") t where rn > {} limit {};".format(
                RN, row)
            # print(sql)
            cur.execute(sql)
            result = cur.fetchall()
            # print(result)
            for res in result:
                di = dict()
                di["rn"] = res[0]
                di["product"] = res[1]
                di["num"] = res[2]
                di["start_time"] = res[3]
                di["finished_time"] = res[4]
                di["recorder"] = res[5]
                di["company"] = res[7]
                di["create_time"] = res[8]
                data.append(di)

            return Response({"total": total, "data": data}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)


class StoreList(APIView):
    """仓库部 制造数据显示 /bg/manufacturing/store/list"""

    # @cache_response(timeout=120, cache="default")
    def get(self, request):
        row = request.query_params.get("row", 10)  # 每页的行数, 默认为10
        page = request.query_params.get("page", 1)  # 第几页, 默认为1
        id = request.query_params.get("id", "")  # 创建人手机号
        name = request.query_params.get("name", "")  # 创建人姓名
        company = request.query_params.get("company", "")  # 所属公司
        RN = (int(page) - 1) * int(row)  # 翻页的起始序号

        id = " t5.phone like '%" + id + "%' and" if id else ""
        name = " t5.username like '%" + name + "%' and" if name else ""
        company = " t5.title like '%" + company + "%'" if company else ""
        condition = (id + name + company).rstrip("and")
        condition = " where " + condition if condition else ''

        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        try:
            data = []

            count_material_incoming_sql = "select count(*) from (select t5.materials, t5.counts, t5.create_time," \
                                          " t5.username, t5.title, t6.time from (select t3.id, t3.materials," \
                                          " t3.counts, t3.create_time, t3.username, t4.title from (select t1.id," \
                                          " t1.factory, t1.materials, t1.counts, t1.create_time, t2.name as username" \
                                          " from (select id, factory, materials, counts, time as create_time," \
                                          " creator_id from material_incoming) t1 left join user_info t2 on" \
                                          " t1.creator_id = t2.phone) t3 left join factorys t4 on t3.factory = t4.id)" \
                                          " t5 left join materials_log t6 on t5.id = t6.use_id) t;"
            cur.execute(count_material_incoming_sql)
            total = cur.fetchone()[0] or 0

            material_incoming_sql = "select * from (select t5.phone, t5.materials, t5.counts, t5.create_time," \
                                    " t5.username, t5.title, t6.time from (select t3.phone, t3.id, t3.materials," \
                                    " t3.counts, t3.create_time, t3.username, t4.title from (select t2.phone, t1.id," \
                                    " t1.factory, t1.materials, t1.counts, t1.create_time, t2.name as username from" \
                                    " (select id, factory, materials, counts, time as create_time, creator_id from" \
                                    " material_incoming) t1 left join user_info t2 on t1.creator_id = t2.phone) t3" \
                                    " left join factorys t4 on t3.factory = t4.id) t5 left join materials_log t6 on" \
                                    " t5.id = t6.use_id" + condition + ") t order by create_time desc;"
            # print("material_incoming_sql=", material_incoming_sql)
            cur.execute(material_incoming_sql)

            cur.execute(material_incoming_sql)
            result_material_incoming = cur.fetchall()
            for result in result_material_incoming:
                di1 = dict()
                li1 = list()
                di1["category"] = "物料"
                di1["inout"] = "入库"
                di1["time"] = result[6] or 0
                di1["recorder"] = result[4] or ""
                di1["company"] = result[5] or ""
                di1["create_time"] = result[3] or 0
                if result[1] and result[2]:
                    for id, count in zip(result[1], result[2]):
                        # print(id, count)
                        sql_name = "select name from material_types where id = '%s';" % id
                        cur.execute(sql_name)
                        result_name = cur.fetchone()
                        name = result_name[0] if result_name else ""
                        name = name if name else ""
                        # print(name)
                        li1.append({"name": name, "number": count})
                        di1["name_number"] = li1
                data.append(di1)

            count_material_outcoming_sql = "select count(*) from (select t5.phone, t5.materials, t5.counts," \
                                           " t5.create_time, t5.username, t5.title, t6.time from (select t3.phone," \
                                           " t3.id, t3.materials, t3.counts, t3.create_time, t3.username, t4.title" \
                                           " from (select t2.phone, t1.id, t1.factory, t1.materials, t1.counts," \
                                           " t1.create_time, t2.name as username from (select id, factory, materials," \
                                           " counts, time as create_time, creator_id from material_outgoing) t1" \
                                           " left join user_info t2 on t1.creator_id = t2.phone) t3 left join" \
                                           " factorys t4 on t3.factory = t4.id) t5 left join materials_log t6 on" \
                                           " t5.id = t6.use_id) t;"
            cur.execute(count_material_outcoming_sql)
            total += cur.fetchone()[0] or 0

            material_outcoming_sql = "select * from (select t5.phone, t5.materials, t5.counts, t5.create_time," \
                                     " t5.username, t5.title, t6.time from (select t3.phone, t3.id, t3.materials," \
                                     " t3.counts, t3.create_time, t3.username, t4.title from (select t2.phone, t1.id," \
                                     " t1.factory, t1.materials, t1.counts, t1.create_time, t2.name as username" \
                                     " from (select id, factory, materials, counts, time as create_time, creator_id" \
                                     " from material_outgoing) t1 left join user_info t2 on t1.creator_id = t2.phone)" \
                                     " t3 left join factorys t4 on t3.factory = t4.id) t5 left join materials_log t6" \
                                     " on t5.id = t6.use_id" + condition + ") t order by create_time desc;"
            # print("material_outcoming_sql=", material_outcoming_sql)
            cur.execute(material_outcoming_sql)
            result_material_outcoming = cur.fetchall()
            # print(result_material_outcoming)
            for result in result_material_outcoming:
                di2 = dict()
                li2 = list()
                di2["category"] = "物料"
                di2["inout"] = "出库"
                di2["time"] = result[6] or 0
                di2["recorder"] = result[4] or ""
                di2["company"] = result[5] or ""
                di2["create_time"] = result[3] or 0
                if result[1] and result[2]:
                    for id, count in zip(result[1], result[2]):
                        # print(id, count)
                        sql_name = "select name from material_types where id = '%s';" % id
                        cur.execute(sql_name)
                        result_name = cur.fetchone()
                        name = result_name[0] if result_name else ""
                        name = name if name else ""
                        # print(name)
                        li2.append({"name": name, "number": count})
                        di2["name_number"] = li2
                data.append(di2)

            count_product_incoming_sql = "select count(*) from (select t5.products, t5.counts, t5.create_time," \
                                         " t5.username, t5.title, t6.time from (select t3.id, t3.products, t3.counts," \
                                         " t3.create_time, t3.username, t4.title from (select t1.id, t1.factory," \
                                         " t1.products, t1.counts, t1.create_time, t2.name as username" \
                                         " from (select id, factory, products, counts, time as create_time," \
                                         " creator_id from product_incoming) t1 left join user_info t2 on" \
                                         " t1.creator_id = t2.phone) t3 left join factorys t4 on t3.factory = t4.id)" \
                                         " t5 left join products_log t6 on t5.id = t6.use_id) t;"
            cur.execute(count_product_incoming_sql)
            total += cur.fetchone()[0] or 0

            product_incoming_sql = "select * from (select t5.phone, t5.products, t5.counts, t5.create_time," \
                                   " t5.username, t5.title, t6.time from (select t3.phone, t3.id, t3.products," \
                                   " t3.counts, t3.create_time, t3.username, t4.title from (select t2.phone,  t1.id," \
                                   " t1.factory, t1.products, t1.counts, t1.create_time, t2.name as username" \
                                   " from (select id, factory, products, counts, time as create_time, creator_id" \
                                   " from product_incoming) t1 left join user_info t2 on t1.creator_id = t2.phone)" \
                                   " t3 left join factorys t4 on t3.factory = t4.id) t5 left join products_log t6" \
                                   " on t5.id = t6.use_id" + condition + ") t order by create_time desc;"
            # print("product_incoming_sql=", product_incoming_sql)
            cur.execute(product_incoming_sql)
            result_product_incoming = cur.fetchall()
            # print(result_product_incoming)
            for result in result_product_incoming:
                di3 = dict()
                li3 = list()
                di3["category"] = "产品"
                di3["inout"] = "入库"
                di3["time"] = result[6] or 0
                di3["recorder"] = result[4] or ""
                di3["company"] = result[5] or ""
                di3["create_time"] = result[3] or 0
                if result[1] and result[2]:
                    for id, count in zip(result[1], result[2]):
                        # print(id, count)
                        sql_name = "select name from products where id = '%s';" % id
                        cur.execute(sql_name)
                        result_name = cur.fetchone()
                        name = result_name[0] if result_name else ""
                        name = name if name else ""
                        # print(name)
                        li3.append({"name": name, "number": count})
                        di3["name_number"] = li3
                data.append(di3)

            count_product_outcoming_sql = "select count(*) from (select t5.products, t5.counts, t5.create_time," \
                                          " t5.username, t5.title, t6.time from (select t3.id, t3.products," \
                                          " t3.counts, t3.create_time, t3.username, t4.title from (select t1.id," \
                                          " t1.factory, t1.products, t1.counts, t1.create_time, t2.name as username" \
                                          " from (select id, factory, products, counts, time as create_time," \
                                          " creator_id from product_outgoing) t1 left join user_info t2 on" \
                                          " t1.creator_id = t2.phone) t3 left join factorys t4 on t3.factory = t4.id)" \
                                          " t5 left join products_log t6 on t5.id = t6.use_id) t;"
            cur.execute(count_product_outcoming_sql)
            total += cur.fetchone()[0] or 0
            # print(total, type(total))
            product_outcoming_sql = "select * from (select t5.phone, t5.products, t5.counts, t5.create_time," \
                                    " t5.username, t5.title, t6.time from (select t3.phone, t3.id, t3.products," \
                                    " t3.counts, t3.create_time, t3.username, t4.title from (select t2.phone, t1.id," \
                                    " t1.factory, t1.products, t1.counts, t1.create_time, t2.name as username" \
                                    " from (select id, factory, products, counts, time as create_time, creator_id" \
                                    " from product_outgoing) t1 left join user_info t2 on t1.creator_id = t2.phone)" \
                                    " t3 left join factorys t4 on t3.factory = t4.id) t5 left join products_log t6" \
                                    " on t5.id = t6.use_id" + condition + ") t order by create_time desc;"
            # print("product_outcoming_sql=", product_outcoming_sql)
            cur.execute(product_outcoming_sql)
            result_product_outcoming = cur.fetchall()
            # print(result_product_outcoming)
            for result in result_product_outcoming:
                di4 = dict()
                li4 = list()
                di4["category"] = "产品"
                di4["inout"] = "出库"
                di4["time"] = result[6] or 0
                di4["recorder"] = result[4] or ""
                di4["company"] = result[5] or ""
                di4["create_time"] = result[3] or 0
                if result[1] and result[2]:
                    for id, count in zip(result[1], result[2]):
                        # print(id, count)
                        sql_name = "select name from products where id = '%s';" % id
                        cur.execute(sql_name)
                        result_name = cur.fetchone()
                        name = result_name[0] if result_name else ""
                        name = name if name else ""
                        # print(name)
                        li4.append({"name": name, "number": count})
                        di4["name_number"] = li4
                data.append(di4)

            # print(data)
            # print(RN, RN + int(row))
            for i, item in enumerate(data):
                item["rn"] = i + 1

            return Response({"total": total, "data": data[RN:RN + int(row)]}, status=status.HTTP_200_OK)
            # return Response({"total": total, "data": data}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)


class XDTask(APIView):
    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        try:
            data = []
            sql_count = "select count(1) from xd_learn_task; "
            cur.execute(sql_count)
            total = cur.fetchone()[0] or 0
            # print(total)
            sql = '''
            select
                t.id,
                t.title,
                t.descr,
                (
                select
                    array_agg(t.keyword)
                from
                    unnest(t.keyword_ids) item_id
                left join xd_image_keyword t on
                    t.id = item_id ) as tags,
                t.images,
                t.state,
                t.time
            from
                xd_learn_task t
            order by
                t.id asc;'''
            cur.execute(sql)
            result = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
            alioss = AliOss()
            for res in result:
                dic = dict()
                for index, col in enumerate(colnames):
                    if col == 'images':
                        dic['images'] = [alioss.joint_image(x) for x in res[index]]
                    else:
                        dic[col] = res[index]
                data.append(dic)
            return Response({"total": total, "data": data}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)

    def post(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        title = request.data.get('title', '')  # 应用名称
        desc = request.data.get('descr', '')  # icon 图像
        keywords = request.data.get('keywords')  # 一句话介绍
        images = request.data.get('images')

        tmp = []
        alioss = AliOss()
        for i in images:
            image_id = alioss.upload_image(i)[0]
            if image_id is not None:
                tmp.append(image_id)
            else:
                continue

        keywords = list(set([str(key) for key in keywords]))
        now = int(time.time())
        images_ids = '{' + ','.join(tmp) + '}'
        keywords = '{' + ','.join(keywords) + '}'

        sql = "insert into xd_learn_task (title, descr, keyword_ids, images, time) values('{0}', " \
              "'{1}', '{2}','{3}', {4})".format(title, desc, keywords, images_ids, now)
        try:
            cur.execute(sql)
            conn.commit()
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '消息添加失败！'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        postgresql.disconnect_postgresql(conn)
        return Response({"res": 0}, status=status.HTTP_200_OK)

    def put(self, request, id):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        state = request.data.get("state")
        if not state:
            return Response({"res": 1, "errmsg": "缺少状态！"}, status=status.HTTP_200_OK)
        if state not in ["0", "1"]:
            return Response({"res": 1, "errmsg": "状态码错误！"}, status=status.HTTP_200_OK)

        try:
            cur.execute("select count(id) from xd_learn_task where id = '%s';" % id)
            result = cur.fetchone()[0]
            if result == 0:
                return Response({"res": 1, "errmsg": "id不存在！"}, status=status.HTTP_200_OK)
            cur.execute("update xd_learn_task set state = '%s' where id = '%s';" % (state, id))
            conn.commit()
            return Response({"res": 0}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)


class XDImageTagKW(APIView):
    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        level = request.query_params.get('type', '1')  # 创建人手机号
        sql = "select id as key, keyword as value from xd_image_keyword where level = '%s' " % level
        data = []
        try:
            cur.execute(sql)
            result = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
            for res in result:
                dic = dict()
                for index, col in enumerate(colnames):
                    dic[col] = res[index]
                data.append(dic)
            return Response({"list": data}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常！'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        typearg = int(request.data.get('type', 0))
        name = request.data.get('name', '')
        image = request.data.get('image', '')
        level, parent = 0, 0

        if typearg == 0:
            level = 1
            parent = 0
        else:
            sql = "select level from xd_image_keyword where id = %d" % typearg
            cur.execute(sql)
            row = cur.fetchone()
            if row is not None:
                level = row[0]
                parent = typearg
            else:
                return Response({'res': 1, 'errmsg': '参数错误！'}, status=status.HTTP_200_OK)

        if not image:
            image_id = ''
        else:
            alioss = AliOss()
            image_id = alioss.upload_image(image)[0]

        now = int(time.time())

        sql = "insert into xd_image_keyword (keyword, image, level, parent, time) values('{0}', " \
              "'{1}', {2}, '{3}', {4})".format(name, image_id, level, parent, now)
        try:
            cur.execute(sql)
            conn.commit()
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常！'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        postgresql.disconnect_postgresql(conn)
        return Response({"res": 0}, status=status.HTTP_200_OK)


class XDImageTag(APIView):
    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        phone = request.query_params.get('phone', '')
        name = request.query_params.get('name', '')
        state = request.query_params.get('state', '')  # 1: 已审核, 0: 未审核
        keyword = request.query_params.get('keyword', '')
        page = int(request.query_params.get('page', 1))  # 第几页
        row = int(request.query_params.get('row', 10))  # 每页行数

        rn = (page - 1) * row
        name = "where t3.name like '%{0}%' ".format(name)
        if phone != '':
            phone = " and t1.phone like '%{0}%'".format(phone)
        if state != '':
            state = " and t1.state = '%s' " % state
        if keyword != '':
            keyword = " and t1.keyword_id = " + str(keyword)

        sql = "select * from ( select t1.id,t1.phone, t3.name, t2.keyword, \
                    t2.image as image1, \
                    t1.image as image2, \
                    t1.time, \
                    t1.state, \
                    t1.err_reason, \
                    row_number() over ( \
                order by \
                    t1.time desc ) as rn \
                from \
                    user_xd_image_tag t1 \
                left join xd_image_keyword t2 on \
                    t1.keyword_id = t2.id \
                left join user_info t3 on \
                    t1.phone = t3.phone {0}{1}{2}{3}".format(name, phone, state,
                                                             keyword) + ") t where rn > %d limit %d" % (rn, row)

        sql_count = "select count(1) from user_xd_image_tag t1 left join user_info t3 on t1.phone = t3.phone {0}{1}{2}{3}".format(
            name, phone, state, keyword)
        data = []
        try:
            cur.execute(sql)
            result = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
            alioss = AliOss()
            for res in result:
                dic = dict()
                for index, col in enumerate(colnames):
                    if col == 'image1' or col == 'image2':
                        dic[col] = alioss.joint_image(res[index])
                    else:
                        dic[col] = res[index]
                data.append(dic)
            cur.execute(sql_count)
            total = cur.fetchone()[0] or 0
            return Response({"data": data, "total": total}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({'res': 1, 'errmsg': '服务器异常！'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, id):
        if not id:
            return Response({"res": 1, "errmsg": "缺少id！"}, status=status.HTTP_200_OK)

        res = request.data.get("res")
        reason = request.data.get("err_reason", '')
        if res == '1':
            state = 2
        elif res == '0':
            state = 1
        else:
            return Response({"res": 1, "errmsg": "缺少参数res！"}, status=status.HTTP_200_OK)

        postgresql = UtilsPostgresql()
        rabbitmq = UtilsRabbitmq()
        conn, cur = postgresql.connect_postgresql()
        
        sql = "update user_xd_image_tag set state = '{0}', err_reason = '{1}' where id = {2}".format(state, reason,
                                                                                                     int(id))
        try:
            cur.execute(sql)
            conn.commit()
            message = {'resource': 'BgXDImagesTag', 'type': 'PUT',
                        'params': {'id': id, 'res': res, 'err_reason': reason}}
            rabbitmq.send_message(json.dumps(message))
            return Response({"res": 0}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)

    def delete(self, request, id):
        if not id:
            return Response({"res": 1, "errmsg": "缺少id！"}, status=status.HTTP_200_OK)
        sql = "delete from user_xd_image_tag where id = {0}".format(id)
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()
        try:
            cur.execute(sql)
            conn.commit()
            return Response({"res": 0}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            postgresql.disconnect_postgresql(conn)
