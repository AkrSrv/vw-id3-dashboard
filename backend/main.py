import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from database import SessionLocal, BatteryLog, Trip, AlarmSettings
from apscheduler.schedulers.background import BackgroundScheduler
import json
import smtplib
from email.message import EmailMessage
import urllib.request
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta

load_dotenv()

app = FastAPI(title="VW ID.3 Dashboard API")

# Allow frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup carconnectivity VW Integration
cc = None
cc_error = None
try:
    if os.environ.get("VW_USERNAME") and os.environ.get("VW_PASSWORD"):
        from carconnectivity import carconnectivity
        cc_config = {
            "carConnectivity": {
                "connectors": [
                    {
                        "type": "volkswagen",
                        "config": {
                            "username": os.environ.get("VW_USERNAME"),
                            "password": os.environ.get("VW_PASSWORD")
                        }
                    }
                ]
            }
        }
        cc = carconnectivity.CarConnectivity(cc_config)
        cc.startup()
except Exception as e:
    cc_error = str(e)
    print("Warning [carconnectivity]:", cc_error)

@app.get("/api/health")
def health_check():
    return {
        "status": "ok", 
        "vw_connected": cc is not None, 
        "error": cc_error
    }

class Credentials(BaseModel):
    username: str
    password: str

@app.post("/api/settings/credentials")
def save_credentials(creds: Credentials):
    global cc, cc_error
    env_path = '/Users/akr/.gemini/antigravity/scratch/vw-id3-dashboard/backend/.env'
    with open(env_path, 'w') as f:
        f.write(f'VW_USERNAME={creds.username}\n')
        f.write(f'VW_PASSWORD={creds.password}\n')
    
    os.environ['VW_USERNAME'] = creds.username
    os.environ['VW_PASSWORD'] = creds.password
    
    # Test connection
    from carconnectivity import carconnectivity
    try:
        new_cc_config = {
            "carConnectivity": {
                "connectors": [
                    {
                        "type": "volkswagen",
                        "config": {
                            "username": creds.username,
                            "password": creds.password
                        }
                    }
                ]
            }
        }
        test_cc = carconnectivity.CarConnectivity(new_cc_config)
        test_cc.startup()
        cc = test_cc
        cc_error = None
        return {"status": "success", "message": "Login approved and connection started!"}
    except Exception as e:
        cc_error = str(e)
        return {"status": "error", "message": f"Server svar: {cc_error}"}

@app.get("/api/vehicle/status")
def get_vehicle_status():
    if not cc or cc_error:
        # Fallback wrapper returning extensive demo data, so the rich UI can be tested
        return {
            "status": "success",
            "message": "Used mock data because live login failed.",
            "data": {
                "battery": {
                    "level": 78,
                    "range_km": 320,
                    "is_charging": True,
                    "charge_power_kw": 48.5,
                    "charge_rate_kmph": 210,
                    "time_to_complete_min": 35,
                    "temperature_c": 22.4,
                    "charge_target": 80,
                    "charge_eta": "2026-04-25T08:00:00Z"
                },
                "climate": {
                    "target_temperature": 21.0,
                    "is_active": True,
                    "outdoor_temperature": 14.5,
                    "climate_eta": "2026-04-25T07:15:00Z",
                    "window_heating_front": True,
                    "window_heating_rear": False
                },
                "vehicle": {
                    "name": "ID.3 (Demo Mode)",
                    "odometer": 15420,
                    "doors_locked": True,
                    "windows_closed": True,
                    "trunk_closed": True,
                    "lights_left_on": False,
                    "lights_right_on": False,
                    "service_inspection_due": 125,
                    "parking": {
                        "latitude": 55.6761,
                        "longitude": 12.5683
                    }
                }
            }
        }
    
    # If connection was successful, pull the data from garage:
    try:
        garage = cc.get_garage()
        children = getattr(garage, 'children', None)
        vehicles = getattr(garage, 'vehicles', None)
        items = children if children else vehicles
        
        if not items:
            if hasattr(cc, 'fetch_all'):
                cc.fetch_all()
            garage = cc.get_garage()
            children = getattr(garage, 'children', None)
            vehicles = getattr(garage, 'vehicles', None)
            items = children if children else vehicles

        if not items:
            return {"status": "error", "message": "Garage is still loading vehicles. Please wait a few seconds and try again."}
            
        vehicle_obj = items[0] if isinstance(items, list) else list(items.values())[0] if isinstance(items, dict) else items[0]
        v = vehicle_obj.as_dict()

        def get_val(*keys, default=None):
            d = v
            for k in keys:
                if isinstance(d, dict) and k in d:
                    d = d[k]
                else:
                    return default
            res = d.get('val', default) if isinstance(d, dict) and 'val' in d else (d if not isinstance(d, dict) else default)
            return res if res is not None else default

        def safe_float(val, default=0.0):
            try:
                if val is None: return default
                return float(val)
            except:
                return default

        name = get_val("name", default="ID.3")
        odometer = safe_float(get_val("odometer", default=0.0))
        
        level = safe_float(get_val("drives", "primary", "level", default=0.0))
        range_km = safe_float(get_val("drives", "primary", "range", default=0.0))
        
        charging_state = get_val("charging", "state", default="")
        is_charging = charging_state in ["ChargingState.CHARGING", "ChargingState.CONSERVATION"]
        
        charge_power = safe_float(get_val("charging", "power", default=0.0))
        
        temp_k = safe_float(get_val("drives", "primary", "battery", "temperature", default=273.15))
        temp_c = temp_k - 273.15
        
        target_temp = safe_float(get_val("climatization", "settings", "target_temperature", default=21.0))
        climate_state = get_val("climatization", "state", default="")
        is_climate_active = climate_state not in ["ClimatizationState.OFF", ""]
        
        lights_left_state = get_val("lights", "left", "light_state", default="LightState.OFF")
        lights_left_on = lights_left_state != "LightState.OFF"
        
        lights_right_state = get_val("lights", "right", "light_state", default="LightState.OFF")
        lights_right_on = lights_right_state != "LightState.OFF"
        
        window_heating_front = get_val("window_heating", "front", "heating_state", default="") not in ["HeatingState.OFF", ""]
        window_heating_rear = get_val("window_heating", "rear", "heating_state", default="") not in ["HeatingState.OFF", ""]
        climate_eta = get_val("climatization", "estimated_date_reached", default=None)
        
        charge_target = safe_float(get_val("charging", "settings", "targetSOC_pct", default=0.0))
        charge_eta = get_val("charging", "estimated_date_reached", default=None)
        
        service_inspection_due = get_val("maintenance", "inspection_due_at", default=None)

        lat = safe_float(get_val("position", "latitude", default=0.0))
        lng = safe_float(get_val("position", "longitude", default=0.0))

        # Defaulting missing access components
        doors_locked = True
        windows_closed = True
        trunk_closed = True

        return {
            "status": "success",
            "data": {
                "battery": {
                    "level": round(level),
                    "range_km": round(range_km),
                    "is_charging": is_charging,
                    "charge_power_kw": charge_power,
                    "charge_rate_kmph": 0,
                    "time_to_complete_min": 0,
                    "temperature_c": round(temp_c, 1),
                    "charge_target": charge_target,
                    "charge_eta": charge_eta
                },
                "climate": {
                    "target_temperature": target_temp,
                    "is_active": is_climate_active,
                    "outdoor_temperature": round(temp_c, 1),
                    "climate_eta": climate_eta,
                    "window_heating_front": window_heating_front,
                    "window_heating_rear": window_heating_rear
                },
                "vehicle": {
                    "name": name,
                    "odometer": round(odometer),
                    "doors_locked": doors_locked,
                    "windows_closed": windows_closed,
                    "trunk_closed": trunk_closed,
                    "lights_left_on": lights_left_on,
                    "lights_right_on": lights_right_on,
                    "service_inspection_due": service_inspection_due,
                    "parking": {
                        "latitude": lat,
                        "longitude": lng
                    }
                }
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Server svar: {str(e)}"}

def background_data_fetch():
    global cc
    if not cc: return
    try:
        garage = cc.get_garage()
        children = getattr(garage, 'children', None)
        vehicles = getattr(garage, 'vehicles', None)
        items = children if children else vehicles
        
        if not items:
            if hasattr(cc, 'fetch_all'): cc.fetch_all()
            garage = cc.get_garage()
            children = getattr(garage, 'children', None)
            vehicles = getattr(garage, 'vehicles', None)
            items = children if children else vehicles
            
        if not items: return
        
        vehicle_obj = items[0] if isinstance(items, list) else list(items.values())[0] if isinstance(items, dict) else items[0]
        v = vehicle_obj.as_dict()

        def get_val(*keys, default=None):
            d = v
            for k in keys:
                if isinstance(d, dict) and k in d: d = d[k]
                else: return default
            res = d.get('val', default) if isinstance(d, dict) and 'val' in d else (d if not isinstance(d, dict) else default)
            return res if res is not None else default

        def safe_float(val, default=0.0):
            try:
                if val is None: return default
                return float(val)
            except:
                return default

        odometer = safe_float(get_val("odometer", default=0.0))
        level = safe_float(get_val("drives", "primary", "level", default=0.0))
        range_km = safe_float(get_val("drives", "primary", "range", default=0.0))
        charging_state = get_val("charging", "state", default="")
        is_charging = 1 if charging_state in ["ChargingState.CHARGING", "ChargingState.CONSERVATION"] else 0
        temp_k = safe_float(get_val("drives", "primary", "battery", "temperature", default=273.15))
        temp_c = temp_k - 273.15

        db = SessionLocal()
        
        # Log battery stats
        log = BatteryLog(
            level=level, 
            range_km=range_km, 
            temperature_c=temp_c, 
            odometer=odometer,
            is_charging=is_charging
        )
        db.add(log)
        
        # Handle trips logic
        last_trip = db.query(Trip).order_by(Trip.id.desc()).first()
        prev_log = db.query(BatteryLog).order_by(BatteryLog.id.desc()).offset(1).first()
        
        if last_trip and last_trip.is_active == 1:
            if odometer > last_trip.end_odometer:
                last_trip.end_odometer = odometer
                last_trip.end_level = level
                last_trip.end_time = datetime.utcnow()
            elif odometer == last_trip.end_odometer:
                time_diff = datetime.utcnow() - (last_trip.end_time or last_trip.start_time)
                if time_diff.total_seconds() > 15 * 60:
                    last_trip.is_active = 0
        else:
            base_odometer = last_trip.end_odometer if last_trip else (prev_log.odometer if prev_log else odometer)
            if base_odometer > 0 and odometer > base_odometer:
                new_trip = Trip(
                    start_time=datetime.utcnow(),
                    start_odometer=base_odometer,
                    start_level=prev_log.level if prev_log else level,
                    end_odometer=odometer,
                    end_level=level,
                    end_time=datetime.utcnow(),
                    is_active=1
                )
                db.add(new_trip)
                
        db.commit()
        db.close()
    except Exception as e:
        import traceback
        print("Scheduler Error:", e)

def check_charge_alarm():
    db = SessionLocal()
    settings = db.query(AlarmSettings).first()
    if not settings or not settings.is_active:
        db.close()
        return
        
    try:
        now_local = datetime.now()
        current_time_str = now_local.strftime("%H:%M")
        current_day = now_local.weekday() # 0 = Monday
        current_date_str = now_local.strftime("%Y-%m-%d")
        
        if settings.time_str == current_time_str and current_date_str != settings.last_triggered_date:
            days_list = json.loads(settings.days) if settings.days else []
            if str(current_day) in days_list or current_day in days_list:
                global cc
                if not cc:
                    db.close()
                    return
                garage = cc.get_garage()
                items = getattr(garage, 'vehicles', None) or getattr(garage, 'children', None)
                if not items:
                    if hasattr(cc, 'fetch_all'): cc.fetch_all()
                    garage = cc.get_garage()
                    items = getattr(garage, 'vehicles', None) or getattr(garage, 'children', None)
                
                if items:
                    vehicle_obj = items[0] if isinstance(items, list) else list(items.values())[0] if isinstance(items, dict) else items[0]
                    v = vehicle_obj.as_dict()
                    
                    def get_val(*keys, default=None):
                        d = v
                        for k in keys:
                            if isinstance(d, dict) and k in d: d = d[k]
                            else: return default
                        res = d.get('val', default) if isinstance(d, dict) and 'val' in d else (d if not isinstance(d, dict) else default)
                        return res if res is not None else default
                    
                    charging_state = get_val("charging", "state", default="")
                    plug_state = get_val("plug", "connectionState", default="")
                    
                    is_plugged = True if plug_state and "CONNECTED" in plug_state.upper() else False
                    is_charging = True if charging_state in ["ChargingState.CHARGING", "ChargingState.CONSERVATION"] else False
                    
                    if not is_plugged and not is_charging:
                        title = "Opladningsalarm"
                        message = "Husk at sætte kablet i bilen til opladning!"
                        
                        # Send Ntfy Push notification
                        if settings.ntfy_topic:
                            try:
                                data = message.encode("utf-8")
                                req = urllib.request.Request(f"https://ntfy.sh/{settings.ntfy_topic}", data=data)
                                req.add_header("Title", title)
                                urllib.request.urlopen(req)
                            except Exception as e:
                                print("Ntfy error:", e)
                                
                        # Send email (Optional if PW is set via env manually)
                        if settings.email_to and os.environ.get("VW_EMAIL_PASS"):
                            try:
                                msg = EmailMessage()
                                msg.set_content(message)
                                msg['Subject'] = title
                                msg['From'] = settings.email_to
                                msg['To'] = settings.email_to
                                s = smtplib.SMTP('smtp-mail.outlook.com', 587)
                                s.starttls()
                                s.login(settings.email_to, os.environ.get("VW_EMAIL_PASS"))
                                s.send_message(msg)
                                s.quit()
                            except Exception as e:
                                print("Email error:", e)
                        
                        settings.last_triggered_date = current_date_str
                        db.commit()
    except Exception as e:
        import traceback
        traceback.print_exc()
    
    db.close()


# Start APScheduler (Slået fra efter brugers ønske for at undgå at spørge bilen hele tiden)
scheduler = BackgroundScheduler()
# scheduler.add_job(background_data_fetch, IntervalTrigger(minutes=5))
scheduler.add_job(check_charge_alarm, IntervalTrigger(minutes=1))
scheduler.start()

class AlarmSettingsSchema(BaseModel):
    days: str
    time_str: str
    email_to: str
    ntfy_topic: str
    is_active: bool

@app.get("/api/settings/alarm")
def get_alarm_settings():
    db = SessionLocal()
    settings = db.query(AlarmSettings).first()
    if not settings:
        settings = AlarmSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    data = {
        "days": settings.days,
        "time_str": settings.time_str,
        "email_to": settings.email_to,
        "ntfy_topic": settings.ntfy_topic,
        "is_active": settings.is_active == 1
    }
    db.close()
    return {"status": "success", "data": data}

@app.post("/api/settings/alarm")
def save_alarm_settings(data: AlarmSettingsSchema):
    db = SessionLocal()
    settings = db.query(AlarmSettings).first()
    if not settings:
        settings = AlarmSettings()
        db.add(settings)
        
    settings.days = data.days
    settings.time_str = data.time_str
    settings.email_to = data.email_to
    settings.ntfy_topic = data.ntfy_topic
    settings.is_active = 1 if data.is_active else 0
    
    db.commit()
    db.close()
    return {"status": "success"}

@app.get("/api/history/battery-temp")
def get_battery_temp(days: int = 5):
    db = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(days=days)
    logs = db.query(BatteryLog).filter(BatteryLog.timestamp >= cutoff).order_by(BatteryLog.timestamp.asc()).all()
    data = [{"t": log.timestamp.isoformat() + "Z", "y": round(log.temperature_c, 1)} for log in logs]
    db.close()
    return {"status": "success", "data": data}

@app.get("/api/history/trips")
def get_trips():
    db = SessionLocal()
    trips = db.query(Trip).order_by(Trip.id.desc()).limit(20).all()
    data = []
    for t in trips:
        data.append({
            "id": t.id,
            "start_time": t.start_time.isoformat() + "Z",
            "end_time": t.end_time.isoformat() + "Z" if t.end_time else None,
            "distance_km": round((t.end_odometer or t.start_odometer) - t.start_odometer, 1),
            "battery_used_pct": round(t.start_level - (t.end_level or t.start_level), 1),
            "is_active": t.is_active == 1
        })
    db.close()
    return {"status": "success", "data": data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
