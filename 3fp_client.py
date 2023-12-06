import asyncio
import tkinter as tk


class Client:
    def __init__(self) -> None:
        self.gui = ''
        self.user = ''

        self.host = 'localhost'
        self.port = 55556

        self.reader = ''
        self.writer = ''

    async def error(self, message):
        print(f"error: {message}")

    async def receive_message(self):
        # Получаем сообщение от сервера
        while True:
            message = await self.reader.read(1024)
            print(f"{message.decode().strip()}")
            await self.gui.receive_message(message.decode().strip())
            if "Connection lost" in message.decode().strip():
                return

    async def send_message(self, message):
        if message == "":
            await self.error("No entries")
            return
        self.writer.write(message.encode())
        await self.writer.drain()
        if message == "/exit":
            return

    async def send_message_to_server(self, writer, message):
        writer.write(message.encode())
        await writer.drain()

    async def start_client(self) -> None:
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        print("Подключено к серверу")

        await self.receive_message()
        self.writer.close()


class GUI:
    def __init__(self, client):
        self.client = client

        self.root = tk.Tk()
        self.root.title("Client")
        self.root['background'] = "green"

        self.scrollbar = tk.Scrollbar(self.root)
        self.scrollbar.pack(side="right", fill="y")

        self.text_widget = tk.Text(self.root, wrap=tk.WORD, yscrollcommand=self.scrollbar.set)
        self.text_widget.pack(fill="both", expand=True)
        self.scrollbar.config(command=self.text_widget.yview)

        self.text_entry = tk.Entry(self.root)
        self.text_entry.pack(side="left", fill="x", expand=True)

        self.send_button = tk.Button(self.root, text="Send", command=self.click)
        self.send_button.pack()

        self.history = list()

    async def update(self, interval=0.05):
        # Обновляем главное окно Tkinter
        while True:
            self.root.update()
            await asyncio.sleep(interval)

    def click(self):
        asyncio.create_task(self.send_message())  # Создаем задачу для отправки сообщения

    async def send_message(self):
        message = self.text_entry.get()
        await self.client.send_message(message)

    async def receive_message(self, message):
        self.text_widget.insert("end", message + '\n')
        self.history.append(message)
        self.text_entry.delete(0, "end")


async def main():
    my_client = Client()
    my_des = GUI(my_client)
    my_client.gui = my_des
    tasks = [
        asyncio.create_task(my_client.start_client()),
        asyncio.create_task(my_des.update())
    ]

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
