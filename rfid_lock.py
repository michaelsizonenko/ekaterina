import asyncio
import socket


async def listen_key():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('192.168.9.43', 9761))
    result = sock.recv(1024)
    print(result.hex())
    await asyncio.sleep(1)
    asyncio.ensure_future(listen_key())


loop = asyncio.get_event_loop()

loop.create_task(listen_key())

try:
    loop.run_forever()
finally:
    loop.close()
