from nakuru.entities.components import Plain, At, Image, Node
from util import general_utils as gu
from util.cmd_config import CmdConfig
import asyncio
from nakuru import (
    CQHTTP,
    GuildMessage
)
import time


class FakeSource:
    def __init__(self, type, group_id):
        self.type = type
        self.group_id = group_id
    
class QQ:
    def __init__(self, is_start: bool, cc: CmdConfig = None, gocq_loop = None) -> None:
        self.is_start = is_start
        self.gocq_loop = gocq_loop
        self.cc = cc
        self.waiting = {}
        self.gocq_cnt = 0

    def run_bot(self, gocq):
        self.client: CQHTTP = gocq
        self.client.run()

    def get_msg_loop(self):
        return self.gocq_loop
    
    def get_cnt(self):
        return self.gocq_cnt
    
    def set_cnt(self, cnt):
        self.gocq_cnt = cnt

    async def send_qq_msg(self, 
                          source, 
                          res,
                          image_mode=None):
        self.gocq_cnt += 1
        if not self.is_start:
            raise Exception("管理员未启动GOCQ平台")
        """
         res可以是一个数组, 也就是gocq的消息链。
         插件开发者请使用send方法, 可以不用直接调用这个方法。
        """
        gu.log("回复GOCQ消息: "+str(res), level=gu.LEVEL_INFO, tag="GOCQ", max_len=300)

        if isinstance(source, int):
            source = FakeSource("GroupMessage", source)
        
        # str convert to CQ Message Chain
        if isinstance(res, str):
            res_str = res
            res = []
            if source.type == "GroupMessage" and not isinstance(source, FakeSource):
                res.append(At(qq=source.user_id))
            res.append(Plain(text=res_str))

        # if image mode, put all Plain texts into a new picture.
        if image_mode is None:
            image_mode = self.cc.get('qq_pic_mode', False)
        if image_mode and isinstance(res, list):
            plains = []
            news = []
            for i in res:
                if isinstance(i, Plain):
                    plains.append(i.text)
                else:
                    news.append(i)
            plains_str = "".join(plains).strip()
            if plains_str != "" and len(plains_str) > 50:
                p = gu.create_markdown_image("".join(plains))
                news.append(Image.fromFileSystem(p))
                res = news

        # 回复消息链
        if isinstance(res, list) and len(res) > 0:
            if source.type == "GuildMessage":
                await self.client.sendGuildChannelMessage(source.guild_id, source.channel_id, res)
                return
            elif source.type == "FriendMessage":
                await self.client.sendFriendMessage(source.user_id, res)
                return
            elif source.type == "GroupMessage":
                # 过长时forward发送
                plain_text_len = 0
                image_num = 0
                for i in res:
                    if isinstance(i, Plain):
                        plain_text_len += len(i.text)
                    elif isinstance(i, Image):
                        image_num += 1
                if plain_text_len > self.cc.get('qq_forward_threshold', 200):
                    # 删除At
                    for i in res:
                        if isinstance(i, At):
                            res.remove(i)
                    node = Node(res)
                    # node.content = res
                    node.uin = 123456
                    node.name = f"bot"
                    node.time = int(time.time())
                    # print(node)
                    nodes=[node]
                    await self.client.sendGroupForwardMessage(source.group_id, nodes)
                    return
                await self.client.sendGroupMessage(source.group_id, res)
                return

    def send(self, 
            to,
            res,
            image_mode=False,
            ):
        '''
        提供给插件的发送QQ消息接口, 不用在外部await。
        参数说明：第一个参数可以是消息对象，也可以是QQ群号。第二个参数是消息内容（消息内容可以是消息链列表，也可以是纯文字信息）。
        第三个参数是是否开启图片模式，如果开启，那么所有纯文字信息都会被合并成一张图片。
        '''
        try:
            asyncio.run_coroutine_threadsafe(self.send_qq_msg(to, res, image_mode), self.gocq_loop).result()
        except BaseException as e:
            raise e
        
    def send_guild(self, 
            message_obj,
            res,
            ):
        '''
        提供给插件的发送GOCQ QQ频道消息接口, 不用在外部await。
        参数说明：第一个参数必须是消息对象, 第二个参数是消息内容（消息内容可以是消息链列表，也可以是纯文字信息）。
        '''
        try:
            asyncio.run_coroutine_threadsafe(self.send_qq_msg(message_obj, res), self.gocq_loop).result()
        except BaseException as e:
            raise e

    def create_text_image(title: str, text: str, max_width=30, font_size=20):
        '''
        文本转图片。
        title: 标题
        text: 文本内容
        max_width: 文本宽度最大值（默认30）
        font_size: 字体大小（默认20）

        返回：文件路径
        '''
        try:
            img = gu.word2img(title, text, max_width, font_size)
            p = gu.save_temp_img(img)
            return p
        except Exception as e:
            raise e

    def wait_for_message(self, group_id):
        '''
        等待下一条消息
        '''
        self.waiting[group_id] = ''
        while True:
            if group_id in self.waiting and self.waiting[group_id] != '':
                # 去掉
                ret = self.waiting[group_id]
                del self.waiting[group_id]
                return ret
            time.sleep(0.5)

    def get_client(self):
        return self.client

    def nakuru_method_invoker(self, func, *args, **kwargs):
        """
        返回一个方法调用器，可以用来立即调用nakuru的方法。
        """
        try:
            ret = asyncio.run_coroutine_threadsafe(func(*args, **kwargs), self.gocq_loop).result()
            return ret
        except BaseException as e:
            raise e

