# -*- coding: utf-8 -*-
import logging
import shortuuid
import oss2
import base64
from django.conf import settings
from itertools import islice
from django.contrib.auth.hashers import make_password, check_password

logger = logging.getLogger('django')


def generate_password(password):
    """生成密码"""
    ps = password
    ge_password = make_password(ps, None, "pbkdf2_sha256")  # 长度77
    # ge_password = make_password(ps, None, "pbkdf2_sha1")  # 长度59
    # print("ge_password=", ge_password)
    # print(len(ge_password))
    return ge_password


def verify_password(password, encryption_password):
    """
    验证密码
    :param password: 用户原始密码
    :param encryption_password: 数据库加密后密码
    :return: 布尔值
    """
    verify_boolean = check_password(password, encryption_password, preferred="pbkdf2_sha256")
    return verify_boolean


def generate_uuid():
    """生成18位短uuid，字符串"""
    # u22 = shortuuid.uuid()  # 22位uuid
    u18 = shortuuid.ShortUUID().random(length=18)  # 18位uuid
    return u18


class AliOss(object):
    """阿里云OSS 图片处理"""
    auth = oss2.Auth('LTAIpVVnnK7jBiAr', '1nDeqBqyUlZzI7njadkgFrpetstdkc')
    bucket = oss2.Bucket(auth, ' https://oss-cn-shenzhen.aliyuncs.com', 'dsd-images')

    def upload_image(self, image):
        """
        上传图片
        :return: 图片id(18位uuid)
        """
        if not image:
            return None, None
        image_id = generate_uuid()
        image_url = "https://dsd-images.oss-cn-shenzhen.aliyuncs.com/{}"
        # print(type(image_id), type(image))
        try:
            if isinstance(image, str) and "," in image:
                image = base64.b64decode(image.split(",")[-1])
                # print(image[:10], type(image))
            else:
                image = None
        except Exception:
            return None, None
        else:
            if image:
                full_image_id = settings.IMAGE_PATH + "/" + image_id + ".jpg"
                AliOss.bucket.put_object(full_image_id, image, headers={"Content-Type": "image/jpg"})

                image_url = image_url.format(full_image_id)
                # print(image_id, full_image_id, image_url)
                return image_id, image_url
            else:
                return None, None

    def joint_image(self, image_id):
        """拼接图片的完整url路径"""
        if not image_id:
            return ""
        image_url = "https://dsd-images.oss-cn-shenzhen.aliyuncs.com/{}"
        full_image_id = settings.IMAGE_PATH + "/" + image_id + ".jpg" if image_id else ''

        return image_url.format(full_image_id)

    def delete_image(self, image_id):
        """
        删除图片
        :return: class:`RequestResult <oss2.models.RequestResult>
        """
        objectname = settings.IMAGE_PATH + "/" + image_id + ".jpg"
        resp = AliOss.bucket.delete_object(objectname)
        return resp

    def exist_image(self, image_id):
        """
        判断文件是否存在
        :return: 返回值为true表示文件存在，false表示文件不存在
        """
        objectname = settings.IMAGE_PATH + "/" + image_id + ".jpg"
        exist = AliOss.bucket.object_exists(objectname)
        return exist

    def list_images(self, num):
        """
        用于遍历文件
        :return: 图片列表
        """
        keys_list = []

        for b in islice(oss2.ObjectIterator(AliOss.bucket), num):
            keys_list.append(b.key)
        return keys_list
