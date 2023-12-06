import asyncio
from datetime import datetime

class ChatServer:
    def __init__(self):
        self.rooms = {}  # Словарь для хранения комнат и их клиентов
        self.clients = set()

    async def send_messages(self, sender, message, room_name):
        # Функция для отправки сообщений всем клиентам в комнате
        tasks = []
        time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for client in self.rooms[room_name]:
            client[0].write(f"{sender[2]}, {time_now}: {message}".encode())
            tasks.append(asyncio.create_task(client[0].drain()))
        await asyncio.gather(*tasks)

    async def send_message(self, writer, response):
        # Функция для отправки сообщения от сервера конкретному клиенту
        writer.write(f"Server message: {response}\n".encode())
        await writer.drain()

    async def broadcast_message(self, client, room, message):
        # Вывод информации о сообщении в консоль
        print(f"Client {client[2]}, from {room}, {message}")

    async def receive_message(self, client, room_name):
        # Функция для приема сообщений от клиента и их передачи в комнату
        while True:
            message = (await client[1].read(1024)).decode().strip()
            await self.broadcast_message(client, room_name, f"sent: {message}")

            if message == "/exit":
                await self.exit(client, room_name)
                return

            await self.send_messages(client, message, room_name)

    async def start_server(self):
        # Запуск сервера и обработка подключений клиентов
        server = await asyncio.start_server(self.handle_client, 'localhost', 55556)
        addr = server.sockets[0].getsockname()
        print(f"Server: {addr}")

        async with server:
            await server.serve_forever()

    async def handle_client(self, reader, writer):
        # Обработка подключения нового клиента
        addr = writer.get_extra_info('peername')
        await self.send_message(writer, "Enter your name")
        name = (await reader.read(1024)).decode().strip()
        client = (writer, reader, name)

        await self.broadcast_message(client, "No room", f"{name} joined the server")
        await self.send_message(writer, f"Your name: {name}\nwrite a /make command to create a room\nwrite a /join to enter a room")

        while True:
            action = (await client[1].read(1024)).decode().strip()
            await self.broadcast_message(client, "No room", f"Entered the command: {action}")

            if action == "/make":
                await self.create_and_enter_room(client)
            elif action == "/join":
                await self.enter_room(client)
            elif action == "/exit":
                await self.exit(client, "no room")
                break
            else:
                await self.send_message(client[0], "Wrong command")

    async def create_and_enter_room(self, client):
        # Создание комнаты и вход в нее
        await self.create_room(client)
        await self.enter_room(client)

    async def enter_room(self, client):
        # Вход в существующую комнату
        while True:
            if not self.rooms:
                # Если нет комнат, предложить создать новую или закрыть соединение
                await self.send_message(client[0], "No rooms available. Do you want to create a room? (yes/no)")
                create_choice = (await client[1].read(1024)).decode().strip()

                if create_choice.lower() == "yes":
                    await self.create_and_enter_room(client)
                    return
                else:
                    await self.send_message(client[0], "Connection lost")
                    return

            all_rooms = "\n".join(self.rooms.keys())
            await self.send_message(client[0], f"Enter the room you want to join:\n{all_rooms}")

            room_name = (await client[1].read(1024)).decode().strip()

            if room_name == "/make":
                await self.create_and_enter_room(client)
                return
            elif room_name in self.rooms:
                if client in self.rooms[room_name]:
                    await self.send_message(client[0], f"You're already in the room {room_name}.")
                else:
                    # Вход в комнату и начало обмена сообщениями
                    self.rooms[room_name].append(client)
                    if (client, "no room") in self.clients:
                        self.clients.remove((client, "no room"))
                    await self.send_message(client[0], f"You joined the room {room_name}. Type '/exit' to leave.")
                    await self.broadcast_message(client, "No room", f"Joined the room {room_name}")
                    await self.send_messages(client, "Joined the room", room_name)
                    await self.receive_message(client, room_name)
                    return
            else:
                await self.send_message(client[0], f"Room '{room_name}' not found. Try again.")

    async def exit(self, client, current_room_name):
        # Выход из текущей комнаты
        await self.send_message(client[0], "Do you want to join another room? (yes/no)")
        exit_choice = (await client[1].read(1024)).decode().strip()

        if exit_choice.lower() == "yes":
            await self.send_message(client[0],
                                    "Do you want to join an existing room or create a new one? (/join--/make)")
            choice = (await client[1].read(1024)).decode().strip()

            # Удаление клиента из текущей комнаты
            if current_room_name in self.rooms:
                self.rooms[current_room_name].remove(client)
                self.clients.remove((client, current_room_name))

            if choice.lower() == "/join":
                await self.join_existing_room(client)
            elif choice.lower() == "/make":
                await self.create_and_enter_room(client)
            else:
                await self.send_message(client[0], "Invalid choice. You will remain in your current room.")
                return
        else:
            await self.send_message(client[0], "Connection lost")
            if current_room_name in self.rooms:
                await self.broadcast_message(client, current_room_name, f"Left the room")
            client[0].close()

    async def join_existing_room(self, client):
        # Присоединение к существующей комнате
        all_rooms = "\n".join(self.rooms.keys())
        await self.send_message(client[0], f"Enter the room you want to join:\n{all_rooms}")

        while True:
            room_name = (await client[1].read(1024)).decode().strip()

            if room_name == "/make":
                await self.create_and_enter_room(client)
                return

            if room_name in self.rooms:
                self.rooms[room_name].append(client)
                await self.send_message(client[0], f"You joined the room {room_name}. Type '/exit' to leave.")
                await self.broadcast_message(client, "No room", f"Joined the room {room_name}")
                await self.send_messages(client, "Joined the room", room_name)
                await self.receive_message(client, room_name)
                return

            await self.send_message(client[0], "Room not found")
            await self.send_message(client[0],
                                    f"Enter the room you want to join or type '/make' to create a new room:\n{all_rooms}")

    async def create_room(self, client):
        # Создание новой комнаты
        await self.send_message(client[0], "Enter the room name")
        while True:
            room_name = (await client[1].read(1024)).decode().strip()
            if room_name in self.rooms:
                await self.send_message(client[0], "This room already exists")
            else:
                self.rooms[room_name] = [client]
                self.clients.add((client, room_name))
                await self.broadcast_message(client, "No room", f"created the room {room_name}")
                await self.send_message(client[0], f"You created and joined the room {room_name}. Type '/exit' to leave.")
                await self.receive_message(client, room_name)
                return

if __name__ == "__main__":
    chat_server = ChatServer()
    asyncio.run(chat_server.start_server())

