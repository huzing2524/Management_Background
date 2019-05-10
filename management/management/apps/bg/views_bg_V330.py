# -*- coding: utf-8 -*-
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps_utils import UtilsPostgresql, UtilsRabbitmq
from constants import INDUSTRY_PLUS_LIST

logger = logging.getLogger('django')


# V3.3.0----------------------------------------------------------------------------------------------------------------


class BgIndustryPlusExamineList(APIView):
    """获取行业+申请列表 /bg/industry_plus/examine"""

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        phone = request.query_params.get('phone', '')
        factory = request.query_params.get('name', '')
        row = request.query_params.get('row', '10')
        page = request.query_params.get('page', '1')

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        template = " {} like '%{}%' "
        if phone and factory:
            condition = 'where' + template.format('contact_phone', phone) + 'and' + template.format('company_name', factory)
        elif phone:
            condition = 'where' + template.format('contact_phone', phone)
        elif factory:
            condition = 'where' + template.format('company_name', factory)
        else:
            condition = ''
        sql = "select * from (select *, row_number() over (order by time desc) as rn from industry_plus_factorys {})t" \
              " where rn > {} order by rn asc limit {};".format(condition, offset, limit)
        sql_count = "select count(1) from (select *, row_number() over (order by time desc) as rn from " \
                    "industry_plus_factorys {})t".format(condition)
        try:
            cur.execute(sql)
            tmp = cur.fetchall()
            data = []
            for i in tmp:
                t = dict()
                t['phone'] = i[0]
                t['factory'] = i[1] or ''
                t['industry'] = i[2] or ''
                t['region'] = i[3] or ''
                t['contact_name'] = i[4] or ''
                t['contact_phone'] = i[5] or ''
                t['problems'] = i[6] or ''
                t['supplement'] = i[7] or []
                t['time'] = i[8]
                t['rn'] = i[9]
                data.append(t)
            cur.execute(sql_count)
            total = cur.fetchone()[0]
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        postgresql.disconnect_postgresql(conn)
        return Response({'data': data, 'total': total}, status=status.HTTP_200_OK)


class BgIndustryPlusTestList(APIView):
    """获取企业智能化测试列表 /bg/industry_plus/test"""

    def get(self, request):
        postgresql = UtilsPostgresql()
        conn, cur = postgresql.connect_postgresql()

        phone = request.query_params.get('phone', '')
        factory = request.query_params.get('name', '')
        row = request.query_params.get('row', '10')
        page = request.query_params.get('page', '1')

        limit = int(row)
        offset = int(row) * (int(page) - 1)

        template = " {} like '%{}%' "
        if phone and factory:
            condition = 'where' + template.format('phone', phone) + 'and' + template.format('company_name', factory)
        elif phone:
            condition = 'where' + template.format('phone', phone)
        elif factory:
            condition = 'where' + template.format('company_name', factory)
        else:
            condition = ''
        sql = "select * from (select *, row_number() over (order by time desc) as rn from industry_plus_test {})t" \
              " where rn > {} order by rn asc limit {};".format(condition, offset, limit)
        sql_count = "select count(1) from (select *, row_number() over (order by time desc) as rn from " \
                    "industry_plus_test {})t".format(condition)
        try:
            cur.execute(sql)
            tmp = cur.fetchall()
            data = []
            for i in tmp:
                t = dict()
                t['phone'] = i[0]
                t['factory'] = i[1] or ''
                t['intelligent_degree'] = []
                t['score'] = i[3]
                t['time'] = i[4]
                t['rn'] = i[5]
                for j in INDUSTRY_PLUS_LIST:
                    if j['key'] in i[2]:
                        t['intelligent_degree'].append(j['value'] + '（完善）')
                    else:
                        t['intelligent_degree'].append(j['value'] + '（欠缺）')
                data.append(t)
            cur.execute(sql_count)
            total = cur.fetchone()[0]
        except Exception as e:
            logger.error(e)
            return Response({"res": 1, "errmsg": "服务器异常！"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        postgresql.disconnect_postgresql(conn)
        return Response({'data': data, 'total': total}, status=status.HTTP_200_OK)
