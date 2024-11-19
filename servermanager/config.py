from mcdreforged.api.all import Serializable, PluginServerInterface
from typing import Type, Dict, List

__all__ = ["Maps","Servers","Config","Map","Server"]

class Base_Config(Serializable):
    __instance = None
    @classmethod
    def get_instance(cls):
        return cls.__instance
    @classmethod
    def set_instance(cls, instance):
        cls.__instance:Type[cls] = instance

class Map(Serializable):
    name: str = ""
    version: List[str] = []

    @classmethod
    def create(cls, name:str, version: List[str]):
        return cls(name, version)

class Server(Serializable):
    name:str = ""
    platform: List[str] = []
    version:str = ""
    note:str = "无"
    java:str = ""
    addion: List[str] = ["-Dfile.encoding=UTF-8","-Duser.language=zh","-Duser.country=CN"]

    def get_java(self) -> str:
        if not self.java:
            return Config.get_java_by_version(self.version)
        else:
            return Config.get_java(self.java)

    def get_addion(self):
        return self.addion
    
    def get_start_cmd(self):
        cmd = [self.get_java()]
        cmd.extend(self.addion)
        cmd.append('-jar server.jar')
        cmd.append('nogui')
        return ' '.join(cmd)
    
    def get_path(self):
        return Servers.get_instance().server_path + self.name

    @classmethod
    def create(cls, name:str, version:str, platform: List[str] = []):
        return cls(name = name, version = version, platform = platform)
    

class Maps(Base_Config):
    map_path:str = "multiservers/maps"
    maps: Dict[str, Map] = {}
    def add(self, name:str, version: List[str]):
        self.maps[name] = Map.create(name, version)

class Servers(Base_Config):
    server_path:str = "./servers/"
    servers: Dict[str, Server] = {}
    def add(self, name:str, version:str, platform: List[str] = []):
        self.servers[name] = Server.create(name, version)
        self.save()

    def get_server(self, name:str) -> Server:
        return self.servers.get(name)
    
    def modify(self, name:str, key:str, value:str):
        server = self.servers.get(name)
        if server is not None:
            if key not in server.serialize().keys():
                return "无效参数"
            if type(server.serialize()[key]) == type(""):
                data = server.serialize()[key] = value
                result = f"服务器{server.name}的{key}已修改为{value}"
            else:
                data = server.serialize()[key] = value.split(',')
                result = f"服务器{server.name}的{key}已修改为{value}"
            self.servers[name] = Server.deserialize(data)
            self.save()
            return result
        else:
            return "服务器不存在"
    
    def save(self):
        PluginServerInterface.get_instance().as_plugin_server_interface().save_config_simple(self,'servers.json')

class Config(Base_Config):
    java:dict = {'Default':'java'}

    @classmethod
    def get_java(cls, java:str):
        try:
            java_exe = cls.java[java]
        except:
            java_exe = cls.java['Default']
        return java_exe
    
    @classmethod
    def get_java_by_version(cls, version:str):
        sub_version = [int(i) for i in version.split('.')]
        match sub_version[1]:
            case x if x<17:
                return cls.get_java('8')
            case x if x>=17&x<20:
                return cls.get_java('17')
            case x if x==20:
                if sub_version[2] == 5:
                    return cls.get_java('21')
                else:
                    return cls.get_java('17')
            case x if x>20:
                return cls.get_java('21')
        

class Config_Manager(Config):
    def __init__(self):
        self.server = PluginServerInterface.get_instance().as_plugin_server_interface()
        self.maps = self.server.load_config_simple("maps.json",target_class=Maps)
        self.servers = self.server.load_config_simple("servers.json",target_class=Servers)
        self.config = self.server.load_config_simple("config.json",target_class=Config)
        Servers.set_instance(self.servers)
        Maps.set_instance(self.maps)
        Config.set_instance(self.config)
    
        

