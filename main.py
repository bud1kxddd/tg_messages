import asyncio
import random
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient
import json

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
    
    def get_random_delay(self):
        """Генерація випадкової затримки від 40 до 90 хвилин"""
        delay_minutes = random.randint(40, 90)
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
    
    async def send_message_to_group(self, group_link, message):
        """Надсилання повідомлення в конкретну групу"""
        try:
            # Витягуємо ідентифікатор групи з посилання
            group_identifier = self.extract_group_identifier(group_link)
            
            # Спроба знайти групу
            entity = await self.client.get_entity(group_identifier)
            await self.client.send_message(entity, message)
            logger.info(f"✅ Повідомлення успішно надіслано в групу: {group_link}")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка при надсиланні в групу {group_link}: {e}")
            return False
    
    async def start_mass_sending(self, cycles=1):
        """Основна функція для масової розсилки"""
        try:
            # Підключення до Telegram
            await self.client.start(phone=self.phone_number)
            logger.info("✅ Успішно підключено до Telegram")
            
            # Завантаження груп і повідомлень
            groups = await self.load_groups()
            messages = self.load_messages()
            
            if not groups:
                logger.error("Список груп порожній!")
                return
            
            if not messages:
                logger.error("Список повідомлень порожній!")
                return
            
            logger.info(f"Початок розсилки в {len(groups)} груп, циклів: {cycles}")
            
            total_successful = 0
            total_failed = 0
            
            for cycle in range(1, cycles + 1):
                logger.info("="*60)
                logger.info(f"🔄 ЦИКЛ {cycle}/{cycles}")
                logger.info("="*60)
                
                cycle_successful = 0
                cycle_failed = 0
                
                for i, group_link in enumerate(groups, 1):
                    # Вибір випадкового повідомлення для кожної групи
                    random_message = random.choice(messages)
                    
                    logger.info(f"[{i}/{len(groups)}] Надсилання в групу: {group_link}")
                    logger.info(f"Повідомлення: {random_message[:50]}...")
                    
                    # Надсилання повідомлення
                    success = await self.send_message_to_group(group_link, random_message)
                    
                    if success:
                        cycle_successful += 1
                        total_successful += 1
                    else:
                        cycle_failed += 1
                        total_failed += 1
                    
                    # Невелика затримка між групами в межах одного циклу (щоб не заблокували)
                    if i < len(groups):
                        small_delay = random.randint(5, 15)  # 5-15 секунд між групами
                        logger.info(f"⏳ Мала затримка: {small_delay} секунд...")
                        await asyncio.sleep(small_delay)
                
                # Статистика циклу
                logger.info("-"*50)
                logger.info(f"📊 СТАТИСТИКА ЦИКЛУ {cycle}:")
                logger.info(f"✅ Успішно надіслано: {cycle_successful}")
                logger.info(f"❌ Помилок: {cycle_failed}")
                logger.info(f"📝 Всього груп в циклі: {len(groups)}")
                logger.info("-"*50)
                
                # Велика затримка після завершення циклу (окрім останнього)
                if cycle < cycles:
                    delay = self.get_random_delay()
                    logger.info(f"🕐 ЗАТРИМКА МІЖ ЦИКЛАМИ: {delay//60} хвилин ({delay} секунд)")
                    logger.info(f"⏰ Наступний цикл почнеться о {(datetime.now() + timedelta(seconds=delay)).strftime('%H:%M:%S')}")
                    await asyncio.sleep(delay)
            
            # Підсумкова статистика всіх циклів
            logger.info("="*60)
            logger.info("🏁 ПІДСУМКОВА СТАТИСТИКА ВСІХ ЦИКЛІВ:")
            logger.info(f"✅ Всього успішно надіслано: {total_successful}")
            logger.info(f"❌ Всього помилок: {total_failed}")
            logger.info(f"🔄 Циклів виконано: {cycles}")
            logger.info(f"📝 Груп в кожному циклі: {len(groups)}")
            logger.info(f"📊 Всього спроб відправки: {cycles * len(groups)}")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Критична помилка: {e}")
        finally:
            await self.client.disconnect()

async def main():
    # Налаштування Telegram API
    # Отримати ці дані можна на https://my.telegram.org/apps
    API_ID = '26812497'  # Замініть на ваш API ID
    API_HASH = '76638ee0a131af4fdf1a388f0b947b78'  # Замініть на ваш API Hash
    PHONE_NUMBER = '+380631420477'  # Замініть на ваш номер телефону (+380XXXXXXXXX)
    
    # Налаштування кількості циклів розсилки
    CYCLES = 1  # Змініть на потрібну кількість циклів (наприклад, 5 для 5 циклів)
    
    if API_ID == 'YOUR_API_ID' or API_HASH == 'YOUR_API_HASH':
        print("❌ Будь ласка, вкажіть ваші дані API в коді!")
        print("Отримати їх можна на https://my.telegram.org/apps")
        return
    
    sender = TelegramSender(API_ID, API_HASH, PHONE_NUMBER)
    await sender.start_mass_sending(cycles=CYCLES)

if __name__ == "__main__":
    asyncio.run(main())