from mcdreforged.api.all import *
from servermanager.config import *
from typing import Callable
from time import sleep
import threading
import os

class CommandManager:
    __instance:'CommandManager' = None
    __on_task = False
    __wait_confirm = False

    def get_server(self, source:CommandSource, name:str, group_id:int = 0) -> Server:
        server = Servers.get_instance().get_server(name)
        if server is None:
            self.response(source, '服务器不存在', group_id = group_id)
            return None
        return server
            
    def response(self, source:CommandSource, message:str, is_broadcast:bool = False, group_id:int = 0):
        if is_broadcast:
            source.get_server().broadcast(message)
        if not group_id and not is_broadcast:
            source.reply(message)
        else:
            try:
                import chatbridge #type:ignore
            except (ImportError, ModuleNotFoundError):
                return
            else:
                send = chatbridge.impl.mcdr.mcdr_entry.send_custom_message
                send(message, group_id)

    def task_confirm(self, source:CommandSource, *, group_id:int = 0):
        if not self.__wait_confirm:
            self.response(source, '目前无任务需要确认', group_id = group_id)
        self.__wait_confirm = False

    def task_complete(self):
        self.__on_task = False

    def task_cancel(self, source:CommandSource, context:CommandContext = {}, group_id:int = 0):
        if not self.__on_task:
            self.response(source, '目前无进行中的任务', group_id = group_id)
        self.__on_task = False

    def __init__(self, server:PluginServerInterface):
        self.server = server
        self.register_command()

    def cmd_welcome(self, source:CommandSource):
        source.reply("Game command")

    def server_list(self, source:CommandSource, *, group_id:int = 0):
        servers = Servers.get_instance().servers
        list = "可用的服务器列表:\n"
        for server in servers.keys():
            list += server+' : '+servers[server].version + '\n'
        self.response(source, list.strip(), group_id = group_id)

    def start_task(self, source:CommandSource, context:CommandContext, task:Callable, group_id:int = 0):
        if self.__on_task:
            self.response(source, '正在执行其他任务，请稍候', group_id = group_id)
            return
        self.__on_task = True
        threading.Thread(target=self.run_task, args=(source, context, task, group_id)).start()

    def run_task(self, source:CommandSource, context:CommandContext, task:Callable, group_id:int = 0):
        try:
            task(source, context, group_id = group_id)
        except Exception as e:
            self.response(source, '任务执行失败', group_id = group_id)
        finally:
            self.task_complete()

    def set_server(self, source:CommandSource, context:CommandContext, group_id:int = 0):
        server = self.get_server(source, context['name'], group_id)
        if server is None:
            return
        self.response(source, f'即将切换至服务器"{server.name}",请在30s内输入!!server confirm确认,或输入!!cancel取消任务', group_id = group_id, is_broadcast=True)
        self.__wait_confirm = True
        for i in range(30):
            sleep(1)
            if not self.__on_task:
                self.response(source, '服务器切换取消', group_id = group_id, is_broadcast=True)
                return
            if not self.__wait_confirm:
                break
        if self.__wait_confirm:
            self.response(source, f'将在20秒后切换至服务器"{server.name}", 发送!!cancel以取消', group_id = group_id, is_broadcast=True)
            return
        self.response(source, f'即将切换至服务器"{server.name}"', group_id = group_id, is_broadcast=True)
        for i in range(20):
            if i < 15 and i%5 == 0 and i != 0:
                source.get_server().broadcast(f'将在{20-i}秒后切换至服务器"{server.name}", 发送!!cancel以取消')
            if i>=15:
                source.get_server().broadcast(f'将在{20-i}秒后切换至服务器"{server.name}", 发送!!cancel以取消')
            sleep(1)
            if not self.__on_task:
                self.response(source, '服务器切换取消', group_id = group_id, is_broadcast=True)
                return
        self.server.modify_mcdr_config({'start_command':server.get_start_cmd(),'working_directory':server.get_path()})
        self.server.restart()

    def create_server(self, source:CommandSource, context:CommandContext, group_id:int = 0):
        if Servers.get_instance().get_server(context['name']) is not None:
            self.response(source, '服务器已存在', group_id = group_id)
            return
        Servers.get_instance().add(context["name"],context["version"])
        os.makedirs(Servers.get_instance().get_server(context['name']).get_path())

    def server_modify(self, source:CommandSource, context:CommandContext, group_id:int = 0):
        result = Servers.get_instance().modify(context['name'], context['key'], context['value'])
        self.response(source, result, group_id = group_id)

    def get_server_info(self, source:CommandSource, context:CommandContext, group_id:int = 0):
        server:Server = Servers.get_instance().get_server(context['name'])
        result = f'服务器"{server.name}"的信息如下:\n'
        result += f'游戏版本: {server.version}\n'
        if server.platform:
            result += f'平台: {"".join(server.platform)}\n'
        if server.java:
            result += f'Java版本: {server.java}\n'
        result += f"服务器备注: {server.note}"
        self.response(source, result, group_id = group_id)

    def set_server_note(self, source:CommandSource, context:CommandContext, group_id:int = 0):
        server = self.get_server(source, context['name'], group_id)
        if server is None:
            return
        server.note = context['value']
        Servers.get_instance().save()
        self.response(source, f'服务器"{server.name}"的备注修改成功"', group_id = group_id)

    @classmethod
    def create(cls, server:PluginServerInterface):
        if cls.__instance is None:
            cls.__instance = cls(server)
        return cls.__instance

    @classmethod
    def get_instance(cls):
        return cls.__instance

    def register_command(self):
        self.server.register_command(
            Literal("!!server").
            runs(self.cmd_welcome).
            then(Literal("list").runs(self.server_list)).
            then(Literal("set").then(
                Text('name').runs(lambda source, context: self.start_task(source, context, self.set_server))
            )).
            then(Literal("modify").then(
                Text('name').then(
                    Text('key').then(
                        GreedyText('value').runs(self.server_modify)
                    )
                )
            )).
            then(Literal("note").then(
                Text('name').then(
                    Text('value').runs(self.set_server_note)
                )
            )).
            then(Literal("info").then(
                Text('name').runs(self.get_server_info)
            )).
            then(Literal("confirm").runs(self.task_confirm)).
            then(Literal("cancel").runs(self.task_cancel)).
            then(Literal("create").then(
                Text('name').then(
                    Text("version").runs(self.create_server)
                )
            ))
        )
        self.server.register_command(Literal("!!cancel").runs(self.task_cancel))
