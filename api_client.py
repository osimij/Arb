import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WinAPIClient:
    """Client for interacting with the 1win API."""
    
    BASE_URL = "https://api.1win.win/v1/client"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make an HTTP request to the API."""
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    # Log the request for debugging
                    logger.info(f"API Request: {method} {url} - Status: {response.status}")
                    
                    try:
                        response_data = await response.json()
                    except:
                        # If JSON parsing fails, get text response
                        response_text = await response.text()
                        logger.error(f"Failed to parse JSON response: {response_text}")
                        return {"success": False, "error": f"Invalid JSON response: {response_text}", "status": response.status}
                    
                    # Success statuses: 200 (OK) and 201 (Created)
                    if response.status in [200, 201]:
                        return {"success": True, "data": response_data}
                    else:
                        return {
                            "success": False,
                            "error": response_data,
                            "status": response.status
                        }
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {e}")
            return {"success": False, "error": f"Network error: {str(e)}"}
        except asyncio.TimeoutError:
            logger.error("Request timed out")
            return {"success": False, "error": "Request timed out"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def _parse_error_message(self, error_data: dict, status: int) -> str:
        """Parse specific error codes from the API with user-friendly Russian descriptions."""
        error_code = error_data.get('errorCode', '')
        error_message = error_data.get('errorMessage', '')
        
        # Handle specific error codes with intuitive Russian explanations
        if status == 400:
            if 'amount exceeds' in error_message.lower() or 'limit' in error_message.lower():
                return (
                    "❌ **Ошибка #400-01: Проблема с суммой депозита**\n\n"
                    "🔍 **Возможные причины:**\n"
                    "• Сумма слишком большая для этого пользователя\n"
                    "• Сумма слишком маленькая (проверьте минимальную сумму)\n"
                    "• У пользователя установлены лимиты на депозиты\n\n"
                    "💡 **Что делать:**\n"
                    "• Попробуйте другую сумму (например, от 100 до 50000)\n"
                    "• Уточните у пользователя его лимиты\n"
                    "• Обратитесь к администратору, если проблема повторяется"
                )
            elif 'deposit already created' in error_message.lower():
                return (
                    "❌ **Ошибка #400-02: Депозит уже создан**\n\n"
                    "ℹ️ У этого пользователя уже есть активный депозит.\n\n"
                    "💡 **Что делать:**\n"
                    "• Дождитесь завершения текущего депозита\n"
                    "• Проверьте статус депозита пользователя\n"
                    "• Если депозит завис, обратитесь к администратору"
                )
            elif 'fee is too high' in error_message.lower():
                return (
                    "❌ **Ошибка #400-03: Комиссия слишком высокая**\n\n"
                    "ℹ️ Комиссия за этот депозит превышает допустимые пределы.\n\n"
                    "💡 **Что делать:**\n"
                    "• Попробуйте меньшую сумму\n"
                    "• Обратитесь к администратору для настройки комиссии"
                )
            elif 'withdrawal is being processed' in error_message.lower():
                return (
                    "❌ **Ошибка #400-04: Вывод уже обрабатывается**\n\n"
                    "ℹ️ У этого пользователя уже есть активный запрос на вывод.\n\n"
                    "💡 **Что делать:**\n"
                    "• Дождитесь завершения текущего вывода\n"
                    "• Проверьте статус вывода пользователя\n"
                    "• Если вывод завис, обратитесь к администратору"
                )
            elif 'incorrect code' in error_message.lower():
                return (
                    "❌ **Ошибка #400-05: Неверный код подтверждения**\n\n"
                    "ℹ️ Код, который ввел пользователь, не подходит.\n\n"
                    "💡 **Что делать:**\n"
                    "• Попросите пользователя проверить код еще раз\n"
                    "• Убедитесь, что код не истек\n"
                    "• Попросите пользователя получить новый код"
                )
            elif 'withdrawal amount exceeds available cash balance' in error_message.lower():
                return (
                    "❌ **Ошибка #400-06: Недостаточно средств в кассе**\n\n"
                    "ℹ️ В кассе нет достаточной суммы для выплаты.\n\n"
                    "💡 **Что делать:**\n"
                    "• Обратитесь к администратору для пополнения кассы\n"
                    "• Предложите пользователю вывести меньшую сумму\n"
                    "• Дождитесь пополнения баланса кассы"
                )
            elif 'invalid cash desk identifier' in error_message.lower():
                return (
                    "❌ **Ошибка #400-07: Проблема с кассой**\n\n"
                    "ℹ️ Идентификатор кассы неверный или касса недоступна.\n\n"
                    "💡 **Что делать:**\n"
                    "• Обратитесь к администратору\n"
                    "• Возможно, касса временно не работает"
                )
            else:
                return (
                    "❌ **Ошибка #400-00: Ошибка в данных**\n\n"
                    "ℹ️ Проверьте правильность введенных данных.\n\n"
                    "💡 **Что проверить:**\n"
                    "• ID пользователя (должен быть числом)\n"
                    "• Сумма (должна быть числом)\n"
                    "• Код подтверждения (для вывода)\n\n"
                    "Если данные верные, обратитесь к администратору."
                )
        
        elif status == 403:
            return (
                "❌ **Ошибка #403: Доступ запрещен**\n\n"
                "ℹ️ Проблема с доступом к системе 1win.\n\n"
                "💡 **Что делать:**\n"
                "• Сообщите администратору о проблеме\n"
                "• Возможно, API ключ нужно обновить\n"
                "• Проверьте интернет соединение"
            )
        
        elif status == 404:
            if error_code == 'CASH02' or 'withdrawal not found' in error_message.lower():
                return (
                    "❌ **Ошибка #404-01: Запрос на вывод не найден**\n\n"
                    "ℹ️ У пользователя нет активного запроса на вывод.\n\n"
                    "💡 **Что делать:**\n"
                    "• Попросите пользователя сначала создать запрос на вывод в приложении 1win\n"
                    "• Убедитесь, что пользователь получил код подтверждения\n"
                    "• Проверьте правильность ID пользователя"
                )
            else:
                return (
                    "❌ **Ошибка #404-02: Пользователь не найден**\n\n"
                    "ℹ️ Пользователь с таким ID не существует в системе 1win.\n\n"
                    "💡 **Что делать:**\n"
                    "• Проверьте правильность ID пользователя\n"
                    "• Попросите пользователя предоставить корректный ID\n"
                    "• Убедитесь, что пользователь зарегистрирован в 1win"
                )
        
        elif status == 429:
            if error_code == 'CASH06' or 'TooManyRequests' in error_message:
                return (
                    "❌ **Ошибка #429-01: Слишком много запросов**\n\n"
                    "ℹ️ Система временно ограничила количество запросов.\n\n"
                    "💡 **Что делать:**\n"
                    "• Подождите 1-2 минуты и попробуйте снова\n"
                    "• Не отправляйте запросы слишком часто\n"
                    "• Если проблема не решается, обратитесь к администратору"
                )
            else:
                return (
                    "❌ **Ошибка #429-02: Превышен лимит запросов**\n\n"
                    "ℹ️ Слишком много операций за короткое время.\n\n"
                    "💡 Попробуйте через несколько минут."
                )
        
        elif status == 500:
            return (
                "❌ **Ошибка #500: Ошибка сервера 1win**\n\n"
                "ℹ️ Проблема на стороне сервера 1win.\n\n"
                "💡 **Что делать:**\n"
                "• Попробуйте через несколько минут\n"
                "• Если проблема повторяется, сообщите администратору\n"
                "• Возможно, сервер 1win временно недоступен"
            )
        
        else:
            return (
                f"❌ **Ошибка #{status}: Неизвестная ошибка**\n\n"
                f"ℹ️ Получена неожиданная ошибка от сервера.\n\n"
                f"💡 **Что делать:**\n"
                f"• Попробуйте еще раз через минуту\n"
                f"• Сообщите администратору об этой ошибке\n"
                f"• Укажите код ошибки: {status}\n\n"
                f"**Техническая информация:** {error_message or 'нет данных'}"
            )
    
    async def create_deposit(self, user_id: int, amount: float) -> Dict[str, Any]:
        """Create a deposit for a user."""
        data = {
            "userId": user_id,
            "amount": amount
        }
        
        result = await self._make_request("POST", "deposit", data)
        
        if not result["success"]:
            error_message = self._parse_error_message(result.get("error", {}), result.get("status", 0))
            return {"success": False, "message": error_message}
        
        # Success case
        deposit_data = result["data"]
        return {
            "success": True,
            "message": f"✅ Депозит успешно создан!\n\n"
                      f"🆔 ID депозита: {deposit_data.get('id')}\n"
                      f"💰 Сумма: {deposit_data.get('amount')}\n"
                      f"👤 ID пользователя: {deposit_data.get('userId')}\n"
                      f"🏦 ID кассы: {deposit_data.get('cashId')}"
        }
    
    async def process_withdrawal(self, user_id: int, code: int) -> Dict[str, Any]:
        """Process a withdrawal for a user with verification code."""
        data = {
            "userId": user_id,
            "code": code
        }
        
        result = await self._make_request("POST", "withdrawal", data)
        
        if not result["success"]:
            error_message = self._parse_error_message(result.get("error", {}), result.get("status", 0))
            return {"success": False, "message": error_message}
        
        # Success case
        withdrawal_data = result["data"]
        return {
            "success": True,
            "message": f"✅ Вывод успешно обработан!\n\n"
                      f"🆔 ID вывода: {withdrawal_data.get('id')}\n"
                      f"💰 Сумма: {withdrawal_data.get('amount')}\n"
                      f"👤 ID пользователя: {withdrawal_data.get('userId')}\n"
                      f"🏦 ID кассы: {withdrawal_data.get('cashId')}"
        }