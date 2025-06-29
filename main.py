import asyncio
import random
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient
from config import API_ID, API_HASH, PHONE_NUMBER
import json
import math

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_sender.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TelegramSender:
    def __init__(self, api_id, api_hash, phone_number):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.client = TelegramClient('session', api_id, api_hash)
    
    async def load_groups(self, filename='groups.txt'):
        """Завантаження списку груп з файлу"""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                groups = [line.strip() for line in file if line.strip()]
            logger.info(f"Завантажено {len(groups)} груп з файлу {filename}")
            return groups
        except FileNotFoundError:
            logger.error(f"Файл {filename} не знайдено!")
            return []
        except Exception as e:
            logger.error(f"Помилка при завантаженні груп: {e}")
            return []
    
    def load_messages(self, filename='messages.txt'):
        """Завантаження списку повідомлень з файлу"""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()
                # Розділяємо повідомлення подвійним переходом на новий рядок
                messages = [msg.strip() for msg in content.split('\n\n') if msg.strip()]
            logger.info(f"Завантажено {len(messages)} повідомлень з файлу {filename}")
            return messages
        except FileNotFoundError:
            logger.error(f"Файл {filename} не знайдено!")
            return []
        except Exception as e:
            logger.error(f"Помилка при завантаженні повідомлень: {e}")
            return []
    
    def randomize_groups(self, groups):
        """Рандомізація порядку груп"""
        randomized_groups = groups.copy()  # Створюємо копію, щоб не змінювати оригінальний список
        random.shuffle(randomized_groups)
        logger.info(f"🎲 Порядок груп рандомізовано для поточного циклу")
        return randomized_groups
    
    def get_random_delay(self):
        """Генерація випадкової затримки від 5 до 10 хвилин"""
        delay_minutes = random.randint(5, 10)
        delay_seconds = delay_minutes * 60
        logger.info(f"Наступна затримка: {delay_minutes} хвилин ({delay_seconds} секунд)")
        return delay_seconds
    
    def extract_group_identifier(self, group_link):
        """Витягує ідентифікатор групи з посилання"""
        if group_link.startswith('https://t.me/'):
            # Витягуємо username з посилання
            return group_link.replace('https://t.me/', '').split('?')[0]
        elif group_link.startswith('@'):
            # Якщо вже є username
            return group_link
        else:
            # Якщо це просто назва або username без @
            return group_link
    
    async def send_message_to_group(self, group_link, message, thread_id=1):
        """Надсилання повідомлення в конкретну групу"""
        try:
            # Витягуємо ідентифікатор групи з посилання
            group_identifier = self.extract_group_identifier(group_link)
            
            # Спроба знайти групу
            entity = await self.client.get_entity(group_identifier)
            await self.client.send_message(entity, message)
            logger.info(f"✅ [Поток {thread_id}] Повідомлення успішно надіслано в групу: {group_link}")
            return True
        except Exception as e:
            logger.error(f"❌ [Поток {thread_id}] Помилка при надсиланні в групу {group_link}: {e}")
            return False
    
    async def process_group_batch(self, groups_batch, messages, thread_id, total_groups):
        """Обробка пакету груп в окремому потоці"""
        thread_successful = 0
        thread_failed = 0
        
        for i, group_link in enumerate(groups_batch, 1):
            # Вибір випадкового повідомлення для кожної групи
            random_message = random.choice(messages)
            
            global_index = (thread_id - 1) * len(groups_batch) + i
            logger.info(f"[Поток {thread_id}] [{global_index}/{total_groups}] Надсилання в групу: {group_link}")
            logger.info(f"[Поток {thread_id}] Повідомлення: {random_message[:50]}...")
            
            # Надсилання повідомлення
            success = await self.send_message_to_group(group_link, random_message, thread_id)
            
            if success:
                thread_successful += 1
            else:
                thread_failed += 1
            
            # Затримка між повідомленнями в потоці (максимум 3 секунди)
            if i < len(groups_batch):
                delay = random.randint(1, 3)  # 1-3 секунди между сообщениями
                logger.info(f"⏳ [Поток {thread_id}] Затримка: {delay} секунд...")
                await asyncio.sleep(delay)
        
        logger.info(f"🧵 [Поток {thread_id}] завершено: ✅{thread_successful} ❌{thread_failed}")
        return thread_successful, thread_failed
    
    def split_groups_into_batches(self, groups, num_threads):
        """Розділення груп на пакети для потоків"""
        batch_size = math.ceil(len(groups) / num_threads)
        batches = []
        
        for i in range(0, len(groups), batch_size):
            batch = groups[i:i + batch_size]
            batches.append(batch)
        
        return batches
    
    async def start_mass_sending(self, cycles=1, num_threads=1):
        """Основна функція для масової розсилки з підтримкою потоків"""
        try:
            # Підключення до Telegram
            await self.client.start(phone=self.phone_number)
            logger.info("✅ Успішно підключено до Telegram")
            
            # Завантаження груп і повідомлень
            original_groups = await self.load_groups()
            messages = self.load_messages()
            
            if not original_groups:
                logger.error("Список груп порожній!")
                return
            
            if not messages:
                logger.error("Список повідомлень порожній!")
                return
            
            # Визначення режиму роботи
            infinite_mode = cycles == 999
            if infinite_mode:
                logger.info(f"🔄 Початок БЕЗКІНЕЧНОЇ розсилки в {len(original_groups)} груп")
                logger.info(f"🧵 Кількість потоків: {num_threads}")
                logger.info("⚠️ Для зупинки натисніть Ctrl+C")
            else:
                logger.info(f"🔄 Початок розсилки в {len(original_groups)} груп, циклів: {cycles}")
                logger.info(f"🧵 Кількість потоків: {num_threads}")
            
            total_successful = 0
            total_failed = 0
            current_cycle = 0
            
            try:
                while True:
                    current_cycle += 1
                    
                    # Перевірка чи не досягнуто ліміт циклів (тільки для скінченного режиму)
                    if not infinite_mode and current_cycle > cycles:
                        break
                    
                    # Рандомізація груп для поточного циклу
                    randomized_groups = self.randomize_groups(original_groups)
                    
                    # Розділення рандомізованих груп на пакети для потоків
                    group_batches = self.split_groups_into_batches(randomized_groups, num_threads)
                    actual_threads = len(group_batches)
                    
                    logger.info("="*60)
                    if infinite_mode:
                        logger.info(f"🔄 ЦИКЛ {current_cycle} (БЕЗКІНЕЧНИЙ РЕЖИМ)")
                    else:
                        logger.info(f"🔄 ЦИКЛ {current_cycle}/{cycles}")
                    logger.info(f"🧵 Запуск {actual_threads} потоків...")
                    logger.info(f"🎲 Груби рандомізовано для цього циклу")
                    logger.info("="*60)
                    
                    # Запуск всіх потоків паралельно
                    tasks = []
                    for thread_id, batch in enumerate(group_batches, 1):
                        task = self.process_group_batch(batch, messages, thread_id, len(randomized_groups))
                        tasks.append(task)
                    
                    # Очікування завершення всіх потоків
                    results = await asyncio.gather(*tasks)
                    
                    # Підрахунок статистики
                    cycle_successful = sum(result[0] for result in results)
                    cycle_failed = sum(result[1] for result in results)
                    
                    total_successful += cycle_successful
                    total_failed += cycle_failed
                    
                    # Статистика циклу
                    logger.info("-"*50)
                    if infinite_mode:
                        logger.info(f"📊 СТАТИСТИКА ЦИКЛУ {current_cycle} (БЕЗКІНЕЧНИЙ):")
                    else:
                        logger.info(f"📊 СТАТИСТИКА ЦИКЛУ {current_cycle}/{cycles}:")
                    logger.info(f"✅ Успішно надіслано: {cycle_successful}")
                    logger.info(f"❌ Помилок: {cycle_failed}")
                    logger.info(f"📝 Всього груп в циклі: {len(randomized_groups)}")
                    logger.info(f"🧵 Потоків використано: {actual_threads}")
                    logger.info(f"🎲 Групи рандомізовано: ТАК")
                    logger.info(f"📈 Загальна статистика: ✅{total_successful} ❌{total_failed}")
                    logger.info("-"*50)
                    
                    # Велика затримка після завершення циклу (5-10 хвилин)
                    # (для безкінечного режиму завжди, для скінченного - окрім останнього)
                    if infinite_mode or current_cycle < cycles:
                        delay = self.get_random_delay()
                        next_time = (datetime.now() + timedelta(seconds=delay)).strftime('%H:%M:%S %d.%m.%Y')
                        
                        if infinite_mode:
                            logger.info(f"🕐 ЗАТРИМКА МІЖ ЦИКЛАМИ: {delay//60} хвилин ({delay} секунд)")
                            logger.info(f"⏰ Наступний цикл {current_cycle + 1} почнеться о {next_time}")
                        else:
                            logger.info(f"🕐 ЗАТРИМКА МІЖ ЦИКЛАМИ: {delay//60} хвилин ({delay} секунд)")
                            logger.info(f"⏰ Наступний цикл {current_cycle + 1}/{cycles} почнеться о {next_time}")
                        
                        await asyncio.sleep(delay)
                        
            except KeyboardInterrupt:
                logger.info("\n" + "="*60)
                logger.info("⚠️ ОТРИМАНО СИГНАЛ ЗУПИНКИ (Ctrl+C)")
                logger.info("🛑 Зупинка розсилки...")
                logger.info("="*60)
            
            # Підсумкова статистика всіх циклів
            logger.info("="*60)
            logger.info("🏁 ПІДСУМКОВА СТАТИСТИКА:")
            logger.info(f"✅ Всього успішно надіслано: {total_successful}")
            logger.info(f"❌ Всього помилок: {total_failed}")
            logger.info(f"🔄 Циклів виконано: {current_cycle}")
            logger.info(f"📝 Груп в кожному циклі: {len(original_groups)}")
            logger.info(f"🧵 Потоків використано: {num_threads}")
            logger.info(f"🎲 Рандомізація груп: УВІМКНЕНА")
            logger.info(f"📊 Всього спроб відправки: {current_cycle * len(original_groups)}")
            if infinite_mode:
                logger.info("♾️ Режим: БЕЗКІНЕЧНИЙ (зупинено користувачем)")
            else:
                logger.info(f"🎯 Режим: СКІНЧЕННИЙ ({cycles} циклів)")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Критична помилка: {e}")
        finally:
            await self.client.disconnect()

def get_cycles_from_user():
    """Отримання кількості циклів від користувача"""
    while True:
        try:
            print("\n" + "="*50)
            print("🔄 НАЛАШТУВАННЯ ЦИКЛІВ РОЗСИЛКИ")
            print("="*50)
            print("1️⃣  Введіть число від 1 до 998 - кількість циклів")
            print("♾️  Введіть 999 - для безкінечної розсилки")
            print("❌ Введіть 0 - для виходу")
            print("-"*50)
            
            user_input = input("Введіть кількість циклів: ").strip()
            
            if not user_input:
                print("❌ Порожній ввід! Спробуйте ще раз.")
                continue
            
            cycles = int(user_input)
            
            if cycles == 0:
                print("👋 Вихід з програми...")
                return None
            elif cycles == 999:
                print("♾️ Обрано БЕЗКІНЕЧНИЙ режим розсилки!")
                print("⚠️ Для зупинки використовуйте Ctrl+C")
                confirm = input("Підтвердити? (y/n): ").strip().lower()
                if confirm in ['y', 'yes', 'так', 'т']:
                    return 999
                else:
                    continue
            elif 1 <= cycles <= 998:
                print(f"✅ Обрано {cycles} циклів розсилки")
                return cycles
            else:
                print("❌ Некоректне значення! Введіть число від 1 до 998, або 999 для безкінечної розсилки.")
                continue
                
        except ValueError:
            print("❌ Некоректний формат! Введіть число.")
        except KeyboardInterrupt:
            print("\n👋 Вихід з програми...")
            return None

def get_threads_from_user():
    """Отримання кількості потоків від користувача"""
    while True:
        try:
            print("\n" + "="*50)
            print("🧵 НАЛАШТУВАННЯ КІЛЬКОСТІ ПОТОКІВ")
            print("="*50)
            print("1️⃣  Введіть число від 1 до 10 - кількість потоків")
            print("⚠️  Рекомендується: 1-3 потоки для уникнення блокування")
            print("-"*50)
            
            user_input = input("Введіть кількість потоків (за замовчуванням 1): ").strip()
            
            if not user_input:
                print("✅ Використовуємо 1 поток за замовчуванням")
                return 1
            
            threads = int(user_input)
            
            if 1 <= threads <= 10:
                if threads > 3:
                    print("⚠️ УВАГА: Використання більше 3 потоків може призвести до блокування!")
                    confirm = input("Продовжити? (y/n): ").strip().lower()
                    if confirm not in ['y', 'yes', 'так', 'т']:
                        continue
                print(f"✅ Обрано {threads} потоків")
                return threads
            else:
                print("❌ Некоректне значення! Введіть число від 1 до 10.")
                continue
                
        except ValueError:
            print("❌ Некоректний формат! Введіть число.")
        except KeyboardInterrupt:
            print("\n👋 Вихід з програми...")
            return None

async def main():
    # Налаштування Telegram API взято з config.py
    # Отримати ці дані можна на https://my.telegram.org/apps
    # Тепер використовуємо імпортовані змінні
    print(f"API_ID: {API_ID}")
    print(f"API_HASH: {API_HASH}")
    print(f"PHONE_NUMBER: {PHONE_NUMBER}")
    
    if API_ID == 'YOUR_API_ID' or API_HASH == 'YOUR_API_HASH':
        print("❌ Будь ласка, вкажіть ваші дані API в коді!")
        print("Отримати їх можна на https://my.telegram.org/apps")
        return
    
    # Отримання кількості циклів від користувача
    cycles = get_cycles_from_user()
    if cycles is None:
        return
    
    # Отримання кількості потоків від користувача
    threads = get_threads_from_user()
    if threads is None:
        return
    
    print("\n🚀 Початок роботи Telegram Sender...")
    print("🎲 Рандомізація груп УВІМКНЕНА - кожен цикл почнеться з різних груп!")
    sender = TelegramSender(API_ID, API_HASH, PHONE_NUMBER)
    await sender.start_mass_sending(cycles=cycles, num_threads=threads)

if __name__ == "__main__":
    asyncio.run(main())