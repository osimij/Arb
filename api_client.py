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
                    response_data = await response.json()
                    
                    if response.status == 200:
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
    
    async def create_deposit(self, user_id: int, amount: float) -> Dict[str, Any]:
        """Create a deposit for a user."""
        data = {
            "userId": user_id,
            "amount": amount
        }
        
        result = await self._make_request("POST", "deposit", data)
        
        if not result["success"]:
            # Handle specific error cases
            if result.get("status") == 400:
                error_msg = result.get("error", {})
                if "Amount exceeds limits" in str(error_msg):
                    return {"success": False, "message": "❌ Сумма превышает лимиты"}
                elif "Deposit already created" in str(error_msg):
                    return {"success": False, "message": "❌ Депозит уже создан для этого пользователя"}
                elif "Deposit fee is too high" in str(error_msg):
                    return {"success": False, "message": "❌ Комиссия за депозит слишком высока"}
                else:
                    return {"success": False, "message": "❌ Неверные данные запроса"}
            elif result.get("status") == 403:
                return {"success": False, "message": "❌ Доступ запрещен. Проверьте API ключ"}
            elif result.get("status") == 404:
                return {"success": False, "message": "❌ Пользователь не найден"}
            else:
                return {"success": False, "message": f"❌ Ошибка API: {result.get('error', 'Unknown error')}"}
        
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
            # Handle specific error cases
            if result.get("status") == 400:
                error_msg = result.get("error", {})
                if "Withdrawal is being processed" in str(error_msg):
                    return {"success": False, "message": "❌ Выводы уже обрабатываются"}
                elif "Amount exceeds limits" in str(error_msg):
                    return {"success": False, "message": "❌ Сумма превышает лимиты"}
                elif "Invalid cash desk identifier" in str(error_msg):
                    return {"success": False, "message": "❌ Неверный идентификатор кассы"}
                elif "Incorrect code" in str(error_msg):
                    return {"success": False, "message": "❌ Неверный код"}
                elif "Withdrawal amount exceeds available cash balance" in str(error_msg):
                    return {"success": False, "message": "❌ Сумма вывода превышает доступный баланс кассы"}
                else:
                    return {"success": False, "message": "❌ Неверные данные запроса"}
            elif result.get("status") == 403:
                return {"success": False, "message": "❌ Доступ запрещен. Проверьте API ключ"}
            elif result.get("status") == 404:
                error_msg = result.get("error", {})
                if "Withdrawal not found" in str(error_msg):
                    return {"success": False, "message": "❌ Вывод не найден"}
                elif "User not found" in str(error_msg):
                    return {"success": False, "message": "❌ Пользователь не найден"}
                else:
                    return {"success": False, "message": "❌ Ресурс не найден"}
            else:
                return {"success": False, "message": f"❌ Ошибка API: {result.get('error', 'Unknown error')}"}
        
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