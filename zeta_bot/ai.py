from typing import *
from openai import OpenAI
import os
import json
import random

from zeta_bot import (
    errors,
    utils,
    console
)

console = console.Console()
level = "Chat AI"

DEFAULT_AI_DIRECTORY_PATH = "./data/ai"

class ChatAI:
    def __init__(self, base_url: str, api_key_str: str, model_name: str, directory_path: str = DEFAULT_AI_DIRECTORY_PATH, ai_name: str = "ZetaBot"):
        # 设置API信息
        self.base_url = base_url
        self.api_key_str = api_key_str
        api_key_str = api_key_str.rstrip("/")
        self.api_key = f"Bearer {api_key_str}"
        self.model_name = model_name
        self.directory_path = directory_path
        utils.create_folder(self.directory_path)
        self.memory_path = f"{self.directory_path}/chat_ai_memories.json"
        self.thread_path = f"{self.directory_path}/threads"
        utils.create_folder(self.thread_path)
        self.ai_name = ai_name

        # 获取系统限定提示词
        if not os.path.exists(f"{self.directory_path}/chat_system_prompt.json"):
            utils.json_save(f"{self.directory_path}/chat_system_prompt.json", utils.json_load("./zeta_bot/ai/default_chat_system_prompt.json"))
        self.system_prompt_str = utils.json_load(f"{self.directory_path}/chat_system_prompt.json")
        self.system_prompt_str = self.system_prompt_str.replace("{bot_name}", self.ai_name)
        self.system_prompt = {
            "role": "system",
            "content": self.system_prompt_str
        }

        # 加载信息
        if not os.path.exists(f"{self.directory_path}/chat_loading_messages.json"):
            utils.json_save(f"{self.directory_path}/chat_loading_messages.json", utils.json_load("./zeta_bot/ai/default_chat_loading_messages.json"))
        self.loading_messages = utils.json_load(f"{self.directory_path}/chat_loading_messages.json")
        for i, message in enumerate(self.loading_messages):
            self.loading_messages[i] = message.replace("{bot_name}", self.ai_name)

        # 无响应信息
        if not os.path.exists(f"{self.directory_path}/chat_no_response_messages.json"):
            utils.json_save(f"{self.directory_path}/chat_no_response_messages.json", utils.json_load("./zeta_bot/ai/default_chat_no_response_messages.json"))
        self.no_response_messages = utils.json_load(f"{self.directory_path}/chat_no_response_messages.json")
        for i, message in enumerate(self.no_response_messages):
            self.no_response_messages[i] = message.replace("{bot_name}", self.ai_name)

        # 错误信息
        if not os.path.exists(f"{self.directory_path}/chat_error_messages.json"):
            utils.json_save(f"{self.directory_path}/chat_error_messages.json", utils.json_load("./zeta_bot/ai/default_chat_error_messages.json"))
        self.error_messages = utils.json_load(f"{self.directory_path}/chat_error_messages.json")
        for i, message in enumerate(self.error_messages):
            self.error_messages[i] = message.replace("{bot_name}", self.ai_name)

        # TODO 让AI访问用户信息了解用户

        # 设置额外记忆
        if os.path.exists(self.memory_path):
            self.memories = utils.json_load(self.memory_path)
        else:
            self.memories = []
            utils.json_save(self.memory_path, self.memories)

        # 设置每个频道的上下文保存
        self.threads = {}
        for root, dirs, files in os.walk(self.thread_path):
            for file in files:
                if file.endswith(".json"):
                    try:
                        thread_id = file.split(".json")[0]
                        messages = utils.json_load(os.path.join(root, file))
                        self.threads[thread_id] = messages
                    except errors.JSONFileError:
                        continue

        # 创建OpenAI实例
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    async def create_thread(self, thread_id: str) -> None:
        if thread_id not in self.threads:
            self.threads[thread_id] = [self.system_prompt]
        if not os.path.exists(f"{self.thread_path}/{thread_id}.json"):
            utils.json_save(f"{self.thread_path}/{thread_id}.json", self.threads[thread_id])

    async def chat(self, thread_id: str, message: str, username: str) -> Dict[str, Union[str, list]]:
        if thread_id not in self.threads:
            await self.create_thread(thread_id)
        # 定期删除对话记录（临时记忆），保留第一个系统限制
        if len(self.threads[thread_id]) > 40:
            self.threads[thread_id] = self.threads[thread_id][0] + self.threads[thread_id][21:]
        # 添加本轮系统限制（稍后移除）
        self.threads[thread_id].append(self.system_prompt)
        # 添加本轮记忆回顾（稍后移除）
        self.threads[thread_id].append({"role": "system", "content": f"以下是你的记忆：{str(self.memories)}"})
        # 添加对话用户说明（已将用户名转移至下方的role为user的content中）
        # self.threads[thread_id].append({"role": "system", "content": f"下面对话的是用户：{username}"})
        # 添加本轮用户对话
        message_content = {"username": username, "message": message}
        self.threads[thread_id].append({"role": "user", "content": str(message_content)})

        # API请求
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.threads[thread_id]
        )
        response = completion.choices[0].message.content

        # 获得API返回内容，截取格式化回复部分
        response = response[response.find("{"):response.rfind("}") + 1]

        try:
            response_dict = json.loads(response)
            response_content = response_dict["message"]

            if response_dict["memories"] is not None and len(response_dict["memories"]) > 0:
                self.memories.append(response_dict["memories"])
                utils.json_save(self.memory_path, self.memories)

            # if response_dict["function_call"] is not None and len(response_dict["function_call"]) > 0:
            #     play_music(response_dict["vars"][0])

        except json.decoder.JSONDecodeError as e:
            response_content = response
            response_dict = {
                "function_call": None,
                "variables": [],
                "message": response_content,
                "memories": None
            }
            await console.rp(f"AI输出格式错误：{response}", level=f"[{level}]", is_error=True)

        # 移除本轮记忆回顾和本轮系统限制（防止AI遗忘限制）
        self.threads[thread_id].pop(-2)
        self.threads[thread_id].pop(-2)

        # 添加本轮API回复
        self.threads[thread_id].append(
            {
                "role": "assistant",
                "content": response_content
            }
        )

        utils.json_save(f"{self.thread_path}/{thread_id}.json", self.threads[thread_id])

        return response_dict

    async def loading_message(self) -> str:
        return self.loading_messages[random.randint(0, len(self.loading_messages) - 1)]

    async def no_response_message(self) -> str:
        return self.no_response_messages[random.randint(0, len(self.no_response_messages) - 1)]
    
    async def error_message(self) -> str:
        return self.error_messages[random.randint(0, len(self.error_messages) - 1)]
    


