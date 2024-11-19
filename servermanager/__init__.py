from mcdreforged.api.all import PluginServerInterface
from servermanager.config import Config_Manager
from servermanager.command import CommandManager

command_manager:CommandManager
def on_load(server: PluginServerInterface, prev):
    global command_manager
    Config_Manager()
    command_manager = CommandManager.create(server)

def on_server_startup(server: PluginServerInterface):
    command_manager.task_complete()
