import asyncio
import RPi.GPIO as GPIO
import sys

loop = None


async def callback_1():
    print("Started looping in callback 1!")
    for i in range(5000):
        await asyncio.sleep(0.01)
    print("Finished looping in callback 1")


async def callback_2():
    await asyncio.sleep(0.01)
    print("Success")


def motion_sensor(callback):
    if loop is None:
        print("Loop is none!")
        return
    asyncio.run_coroutine_threadsafe(callback(), loop)
    # loop.call_soon_threadsafe(message_manager_f)


if __name__ == '__main__':
    try:
        print("Starting asyncio...")

        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(21, GPIO.IN)
        GPIO.add_event_detect(21, GPIO.BOTH, callback=lambda x: motion_sensor(callback_2))

        GPIO.setup(26, GPIO.IN)
        GPIO.add_event_detect(26, GPIO.BOTH, callback=lambda x: motion_sensor(callback_1))

        loop = asyncio.get_event_loop()
        loop.run_forever()
        loop.close()
    except:
        print("Error:", sys.exc_info()[0])
    finally:
        GPIO.cleanup()
