"""
/api/weather — 天气 + 农事建议（完全免费，无需 API Key）
天气数据: Open-Meteo (https://open-meteo.com)
地名反查: OpenStreetMap Nominatim
"""
import httpx
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/weather", tags=["天气"])

# ── WMO 天气代码 → 中文描述 ──
WMO_CODE_MAP = {
    0: "晴", 1: "大部晴", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻雨", 67: "大冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "小阵雨", 81: "阵雨", 82: "大阵雨",
    85: "小阵雪", 86: "大阵雪",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "强雷阵雨伴冰雹",
}

# ── 农事建议映射 ──
FARM_TIPS = {
    "晴": "天气晴好，适合田间作业和喷施农药。注意做好灌溉补水。",
    "多云": "天气多云，适合一般田间管理和施肥作业。",
    "阴": "阴天光照不足，注意大棚通风透光，预防真菌类病害。",
    "小雨": "小雨天气，不宜喷洒农药。可进行室内育苗或准备农资。",
    "中雨": "中雨天气，注意田间排水防涝，暂停户外作业。",
    "大雨": "大雨天气，请做好防洪排涝工作！注意检查大棚设施。",
    "暴雨": "暴雨预警！请做好防灾减灾工作，加固温室大棚，确保排水畅通。",
    "雷阵雨": "有雷阵雨，请暂停户外作业，注意人身安全。",
    "雪": "降雪天气，注意温室保温防冻，及时清除棚面积雪。",
    "雾": "有雾天气，湿度大，注意预防霜霉病等真菌病害。",
    "雨": "雨天不宜喷洒农药，注意田间排水。",
}


def get_weather_text(code: int) -> str:
    return WMO_CODE_MAP.get(code, "未知")


def get_farm_tip(weather_text: str, temp: float = None) -> str:
    for key, tip in FARM_TIPS.items():
        if key in weather_text:
            return tip
    if temp is not None:
        if temp <= 0:
            return "低温天气，注意作物防冻保温，大棚加盖保温层。"
        elif temp >= 35:
            return "高温天气，注意遮阳降温，增加灌溉频次，避免中午作业。"
    return "关注天气变化，合理安排农事活动。"


# ── 风向 ──
def degree_to_direction(deg: float) -> str:
    dirs = ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"]
    idx = int((deg + 22.5) / 45) % 8
    return dirs[idx]


async def reverse_geocode(lat: float, lon: float) -> str:
    """通过 Nominatim 免费反查地名"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": lat, "lon": lon,
                    "format": "json",
                    "accept-language": "zh-CN",
                    "zoom": 10,
                },
                headers={"User-Agent": "CropDiseaseApp/1.0"},
                timeout=8,
            )
            data = resp.json()
            addr = data.get("address", {})
            city = addr.get("city", "") or addr.get("county", "") or addr.get("state", "")
            district = addr.get("suburb", "") or addr.get("district", "")
            if city and district:
                return f"{city} {district}"
            return city or data.get("display_name", "").split(",")[0]
    except Exception:
        return ""


@router.get("/now")
async def get_weather(
    lat: float = Query(..., description="纬度"),
    lon: float = Query(..., description="经度"),
):
    """
    获取当前天气 + 农事建议（全免费）
    - 天气数据来源: Open-Meteo (无需 API Key)
    - 地名来源: OpenStreetMap Nominatim (无需 API Key)
    """
    city_name = ""
    weather_text = "多云"
    temp = 22.0
    humidity = 65
    wind_speed = 5.0
    wind_dir = 0.0

    async with httpx.AsyncClient() as client:
        # 1. 获取真实天气 (Open-Meteo 完全免费)
        try:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": "true",
                    "hourly": "relativehumidity_2m",
                    "forecast_days": 1,
                    "timezone": "auto",
                },
                timeout=10,
            )
            data = resp.json()
            cw = data.get("current_weather", {})
            temp = cw.get("temperature", 22)
            wind_speed = cw.get("windspeed", 5)
            wind_dir = cw.get("winddirection", 0)
            wmo_code = cw.get("weathercode", 2)
            weather_text = get_weather_text(wmo_code)

            # 取当前时刻的湿度
            hourly = data.get("hourly", {})
            rh_list = hourly.get("relativehumidity_2m", [])
            if rh_list:
                humidity = rh_list[0]
        except Exception:
            pass

        # 2. 反查地名
        try:
            geo_resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": lat, "lon": lon,
                    "format": "json",
                    "accept-language": "zh-CN",
                    "zoom": 10,
                },
                headers={"User-Agent": "CropDiseaseApp/1.0"},
                timeout=8,
            )
            geo_data = geo_resp.json()
            addr = geo_data.get("address", {})
            city = addr.get("city", "") or addr.get("county", "") or addr.get("state", "")
            district = addr.get("suburb", "") or addr.get("district", "")
            if city and district:
                city_name = f"{city} {district}"
            else:
                city_name = city or geo_data.get("display_name", "").split(",")[0]
        except Exception:
            pass

    # 风力等级 (简化: 风速 km/h → 等级)
    wind_scale = "1"
    if wind_speed >= 62:
        wind_scale = "8"
    elif wind_speed >= 39:
        wind_scale = "6"
    elif wind_speed >= 29:
        wind_scale = "5"
    elif wind_speed >= 20:
        wind_scale = "4"
    elif wind_speed >= 12:
        wind_scale = "3"
    elif wind_speed >= 6:
        wind_scale = "2"

    return {
        "location": city_name or "未知地区",
        "temp": str(int(temp)),
        "text": weather_text,
        "icon": "",
        "humidity": str(humidity),
        "wind_dir": degree_to_direction(wind_dir),
        "wind_scale": wind_scale,
        "farm_tip": get_farm_tip(weather_text, temp),
    }

