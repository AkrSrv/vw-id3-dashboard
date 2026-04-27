const API_BASE = 'http://' + window.location.hostname + ':8000';
const API_URL = `${API_BASE}/api/vehicle/status`;

// DOM Elements
const syncDot = document.getElementById('sync-status');
const syncText = document.getElementById('sync-text');
const lastUpdated = document.getElementById('last-updated');
const vehicleTitle = document.getElementById('vehicle-title');

// Battery Elements
const batteryLevel = document.getElementById('battery-level');
const batteryProgress = document.getElementById('battery-progress');
const rangeKm = document.getElementById('range-km');
const battTemp = document.getElementById('batt-temp');
const chargePower = document.getElementById('charge-power');
const timeLeft = document.getElementById('time-left');
const chargeTarget = document.getElementById('charge-target');
const chargeEta = document.getElementById('charge-eta');

// Climate Elements
const targetTemp = document.getElementById('target-temp');
const outdoorTemp = document.getElementById('outdoor-temp');
const climateStateBadge = document.getElementById('climate-state-badge');
const windowHeatFront = document.getElementById('window-heat-front');
const windowHeatRear = document.getElementById('window-heat-rear');
const climateEta = document.getElementById('climate-eta');

// Vehicle Info Elements
const doorsLocked = document.getElementById('doors-locked');
const windowsClosed = document.getElementById('windows-closed');
const trunkClosed = document.getElementById('trunk-closed');
const lightsLeftOn = document.getElementById('lights-left-on');
const lightsRightOn = document.getElementById('lights-right-on');
const odometer = document.getElementById('odometer');
const serviceDue = document.getElementById('service-due');
const parkingLocation = document.getElementById('parking-location');

// Modal Elements
const settingsModal = document.getElementById('settings-modal');
const openSettingsBtn = document.getElementById('open-settings-btn');
const closeSettingsBtn = document.getElementById('close-settings-btn');
const saveCredsBtn = document.getElementById('save-credentials-btn');
const vwUsername = document.getElementById('vw-username');
const vwPassword = document.getElementById('vw-password');
const authResult = document.getElementById('auth-result');

/**
 * Fetch status from our Python backend
 */
async function fetchVehicleStatus() {
  try {
    syncText.textContent = 'Syncing...';
    syncDot.className = 'status-dot';
    
    const response = await fetch(API_URL);
    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status}`);
    }
    
    const json = await response.json();
    if (json.status === 'success') {
      updateDashboard(json.data);
      
      syncText.textContent = 'Online';
      syncDot.className = 'status-dot online';
      
      const now = new Date();
      lastUpdated.textContent = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
    } else {
      throw new Error('API returned failure status');
    }
    
  } catch (err) {
    console.error('Failed to fetch vehicle status:', err);
    syncText.textContent = 'Offline';
    syncDot.className = 'status-dot error';
  }
}

function formatEtaTime(isoOrValue) {
  if(isoOrValue === null || isoOrValue === undefined || isoOrValue === "") return "N/A";
  const d = new Date(isoOrValue);
  if(isNaN(d.getTime())) return isoOrValue; 
  return d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

/**
 * Update the UI with fetched data
 */
function updateDashboard(data) {
  // Vehicle Info
  const vehicleInfo = data.vehicle;
  vehicleTitle.textContent = vehicleInfo.name;

  // Battery
  const batteryInfo = data.battery;
  animateValue(batteryLevel, parseInt(batteryLevel.innerText) || 0, batteryInfo.level, 1000);
  batteryProgress.style.width = `${batteryInfo.level}%`;
  
  // Color the progress bar based on level
  if (batteryInfo.level <= 20) {
    batteryProgress.style.background = 'linear-gradient(90deg, #ef4444, #f87171)'; // Red
  } else if (batteryInfo.level <= 50) {
    batteryProgress.style.background = 'linear-gradient(90deg, #f59e0b, #fbbf24)'; // Orange
  } else {
    batteryProgress.style.background = 'linear-gradient(90deg, #10b981, #34d399)'; // Green
  }

  // Detailed Grid
  rangeKm.textContent = `${batteryInfo.range_km} km`;
  battTemp.textContent = `${batteryInfo.temperature_c.toFixed(1)} °C`;
  
  if(batteryInfo.is_charging) {
    chargePower.textContent = `${batteryInfo.charge_power_kw} kW`;
    timeLeft.textContent = `${batteryInfo.time_to_complete_min} min`;
    chargePower.parentElement.style.opacity = '1';
    timeLeft.parentElement.style.opacity = '1';
  } else {
    chargePower.textContent = `0 kW`;
    timeLeft.textContent = `N/A`;
    chargePower.parentElement.style.opacity = '0.4';
    timeLeft.parentElement.style.opacity = '0.4';
  }
  
  chargeTarget.textContent = batteryInfo.charge_target ? `${batteryInfo.charge_target}%` : '--%';
  chargeEta.textContent = formatEtaTime(batteryInfo.charge_eta);

  // Climate
  const climateInfo = data.climate;
  targetTemp.textContent = climateInfo.target_temperature.toFixed(1);
  outdoorTemp.textContent = `${climateInfo.outdoor_temperature.toFixed(1)} °C`;
  
  if (climateInfo.is_active) {
    climateStateBadge.textContent = 'Status: Active';
    climateStateBadge.style.background = 'rgba(16, 185, 129, 0.2)';
    climateStateBadge.style.color = '#34d399';
  } else {
    climateStateBadge.textContent = 'Status: Off';
    climateStateBadge.style.background = 'rgba(255, 255, 255, 0.1)';
    climateStateBadge.style.color = '#fff';
  }
  
  windowHeatFront.innerHTML = climateInfo.window_heating_front ? '<span style="color: #f59e0b;">Tændt</span>' : 'Slukket';
  windowHeatRear.innerHTML = climateInfo.window_heating_rear ? '<span style="color: #f59e0b;">Tændt</span>' : 'Slukket';
  climateEta.textContent = formatEtaTime(climateInfo.climate_eta);

  // Vehicle Security
  doorsLocked.innerHTML = vehicleInfo.doors_locked 
    ? '<span style="color: #10b981;"><i class="fa-solid fa-lock"></i> Locked</span>' 
    : '<span style="color: #ef4444;"><i class="fa-solid fa-lock-open"></i> Unlocked</span>';
    
  windowsClosed.innerHTML = vehicleInfo.windows_closed 
    ? '<span style="color: #10b981;"><i class="fa-solid fa-check"></i> Closed</span>' 
    : '<span style="color: #ef4444;"><i class="fa-solid fa-xmark"></i> Open</span>';

  trunkClosed.innerHTML = vehicleInfo.trunk_closed 
    ? '<span style="color: #10b981;"><i class="fa-solid fa-check"></i> Closed</span>' 
    : '<span style="color: #ef4444;"><i class="fa-solid fa-xmark"></i> Open</span>';
    
  lightsLeftOn.innerHTML = vehicleInfo.lights_left_on
    ? '<span style="color: #f59e0b;"><i class="fa-solid fa-lightbulb"></i> On</span>'
    : '<span style="color: #10b981;"><i class="fa-regular fa-lightbulb"></i> Off</span>';

  lightsRightOn.innerHTML = vehicleInfo.lights_right_on
    ? '<span style="color: #f59e0b;"><i class="fa-solid fa-lightbulb"></i> On</span>'
    : '<span style="color: #10b981;"><i class="fa-regular fa-lightbulb"></i> Off</span>';

  odometer.textContent = `${vehicleInfo.odometer.toLocaleString()} km`;
  
  if (vehicleInfo.service_inspection_due !== undefined && vehicleInfo.service_inspection_due !== null) {
      serviceDue.textContent = typeof vehicleInfo.service_inspection_due === 'number' 
        ? `${vehicleInfo.service_inspection_due} dage` 
        : vehicleInfo.service_inspection_due;
  } else {
      serviceDue.textContent = "Ukendt";
  }

  // Parking target
  if(vehicleInfo.parking && vehicleInfo.parking.latitude) {
      parkingLocation.href = `https://www.google.com/maps/search/?api=1&query=${vehicleInfo.parking.latitude},${vehicleInfo.parking.longitude}`;
      parkingLocation.innerHTML = `Map <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:0.8rem"></i>`;
      parkingLocation.style.pointerEvents = 'auto';
      parkingLocation.style.opacity = '1';
  } else {
      parkingLocation.href = '#';
      parkingLocation.innerHTML = `Unknown`;
      parkingLocation.style.pointerEvents = 'none';
      parkingLocation.style.opacity = '0.5';
  }
}

/**
 * Animate numbers counting up/down smoothly
 */
function animateValue(obj, start, end, duration) {
  if (start === end) return;
  const range = end - start;
  let current = start;
  const increment = end > start ? 1 : -1;
  const stepTime = Math.abs(Math.floor(duration / range));
  
  if(stepTime === Infinity || stepTime <= 0) return;

  const timer = setInterval(function() {
    current += increment;
    obj.innerHTML = current;
    if (current == end) {
      clearInterval(timer);
    }
  }, stepTime);
}

// Initial fetch
document.addEventListener('DOMContentLoaded', () => {
  fetchVehicleStatus();
  // Poll every 30 seconds - SLÅET FRA pga. brugerønske
  // setInterval(fetchVehicleStatus, 30000);
});

// Interactive Elements
document.getElementById('refresh-btn').addEventListener('click', () => {
    fetchVehicleStatus();
    if(document.querySelector('.history-btn.active')) {
        fetchHistory(document.querySelector('.history-btn.active').dataset.days);
    }
    fetchTrips();
});

document.getElementById('toggle-climate-btn').addEventListener('click', () => {
    alert('Climate Control toggled! (Functionality pending live connection)');
});

// Settings Modal Logic
openSettingsBtn.addEventListener('click', () => {
  settingsModal.classList.remove('hidden');
  authResult.classList.add('hidden');
});

closeSettingsBtn.addEventListener('click', () => {
  settingsModal.classList.add('hidden');
});

saveCredsBtn.addEventListener('click', async () => {
  const user = vwUsername.value.trim();
  const pass = vwPassword.value;
  if (!user || !pass) {
    showAuthResult('error', 'Udfyld venligst både e-mail og adgangskode.');
    return;
  }
  
  saveCredsBtn.disabled = true;
  saveCredsBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Forbinder...';
  authResult.classList.add('hidden');
  
  try {
    const res = await fetch(`${API_BASE}/api/settings/credentials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: user, password: pass })
    });
    
    const data = await res.json();
    if (data.status === 'success') {
      showAuthResult('success', data.message);
      // Immediately refresh dashboard
      fetchVehicleStatus();
      setTimeout(() => settingsModal.classList.add('hidden'), 2000);
    } else {
      showAuthResult('error', data.message);
    }
  } catch (err) {
    showAuthResult('error', 'Netværksfejl ved forbindelse til backenden: ' + err.message);
  } finally {
    saveCredsBtn.disabled = false;
    saveCredsBtn.innerHTML = 'Gem og Tilslut <i class="fa-solid fa-arrow-right-to-bracket"></i>';
  }
});

function showAuthResult(type, message) {
  authResult.textContent = message;
  authResult.className = `auth-result ${type}`;
}

// ---------------------------
// Alarm Modal Logic
// ---------------------------
const openAlarmBtn = document.getElementById('open-alarm-btn');
const closeAlarmBtn = document.getElementById('close-alarm-btn');
const alarmSettingsModal = document.getElementById('alarm-settings-modal');
const saveAlarmBtn = document.getElementById('save-alarm-btn');
const alarmAuthResult = document.getElementById('alarm-auth-result');

openAlarmBtn.addEventListener('click', async () => {
  alarmSettingsModal.classList.remove('hidden');
  alarmAuthResult.classList.add('hidden');
  document.getElementById('alarm-active').checked = false; // Reset first
  
  try {
    saveAlarmBtn.disabled = true;
    const res = await fetch(`${API_BASE}/api/settings/alarm`);
    const json = await res.json();
    if(json.status === 'success') {
       document.getElementById('alarm-active').checked = json.data.is_active;
       if(json.data.time_str) document.getElementById('alarm-time').value = json.data.time_str;
       if(json.data.ntfy_topic) document.getElementById('alarm-ntfy').value = json.data.ntfy_topic;
       if(json.data.email_to) document.getElementById('alarm-email').value = json.data.email_to;
       
       let days = [];
       if(json.data.days) {
           try { days = JSON.parse(json.data.days); } catch(e) {}
       }
       document.querySelectorAll('.day-cb').forEach(cb => {
         cb.checked = days.includes(cb.value);
       });
    }
  } catch (e) { console.error(e); } finally {
      saveAlarmBtn.disabled = false;
  }
});

closeAlarmBtn.addEventListener('click', () => {
    alarmSettingsModal.classList.add('hidden');
});

saveAlarmBtn.addEventListener('click', async () => {
    const is_active = document.getElementById('alarm-active').checked;
    const time_str = document.getElementById('alarm-time').value;
    const ntfy_topic = document.getElementById('alarm-ntfy').value;
    const email_to = document.getElementById('alarm-email').value;
    
    const days = [];
    document.querySelectorAll('.day-cb:checked').forEach(cb => days.push(cb.value));
    
    saveAlarmBtn.disabled = true;
    saveAlarmBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Gemmer...';
    try {
        const res = await fetch(`${API_BASE}/api/settings/alarm`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                days: JSON.stringify(days),
                time_str: time_str, 
                ntfy_topic: ntfy_topic, 
                email_to: email_to, 
                is_active: is_active
            })
        });
        const json = await res.json();
        if(json.status === 'success') {
            alarmAuthResult.textContent = "Alarm indstillinger gemt!";
            alarmAuthResult.className = `auth-result success`;
            alarmAuthResult.classList.remove('hidden');
            setTimeout(() => { alarmSettingsModal.classList.add('hidden'); }, 1500);
        } else {
            throw new Error(json.message || "Fejl under gem");
        }
    } catch(err) {
        alarmAuthResult.textContent = "Fejl: " + err.message;
        alarmAuthResult.className = `auth-result error`;
        alarmAuthResult.classList.remove('hidden');
    } finally {
        saveAlarmBtn.disabled = false;
        saveAlarmBtn.innerHTML = 'Gem Alarm <i class="fa-solid fa-floppy-disk"></i>';
    }
});

// ---------------------------
// History and Chart Logic
// ---------------------------
let tempChartInstance = null;

async function fetchHistory(days = 5) {
  try {
    const res = await fetch(`${API_BASE}/api/history/battery-temp?days=${days}`);
    const json = await res.json();
    if(json.status === 'success') {
      renderChart(json.data);
    }
  } catch (err) {
    console.error('Failed to fetch history:', err);
  }
}

function renderChart(data) {
  const ctx = document.getElementById('tempChart').getContext('2d');
  
  const labels = data.map(d => {
    const date = new Date(d.t);
    return date.toLocaleString([], {month: 'short', day: 'numeric', hour: '2-digit', minute:'2-digit'});
  });
  const points = data.map(d => d.y);

  if(tempChartInstance) {
    tempChartInstance.data.labels = labels;
    tempChartInstance.data.datasets[0].data = points;
    tempChartInstance.update();
    return;
  }

  tempChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Batteri Temp (°C)',
        data: points,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.2)',
        borderWidth: 2,
        tension: 0.4,
        fill: true,
        pointRadius: 0,
        pointHitRadius: 10
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: { 
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8', maxTicksLimit: 6 }
        },
        y: { 
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8' }
        }
      }
    }
  });
}

// History Controls
const historyBtns = document.querySelectorAll('.history-btn');
historyBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    historyBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    fetchHistory(btn.dataset.days);
  });
});

// ---------------------------
// Trips Logic
// ---------------------------
async function fetchTrips() {
  try {
    const res = await fetch(`${API_BASE}/api/history/trips`);
    const json = await res.json();
    if(json.status === 'success') {
      const tbody = document.getElementById('trips-body');
      tbody.innerHTML = '';
      
      if(json.data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-secondary);">Ingen ture logget endnu.</td></tr>';
        return;
      }
      
      json.data.forEach(trip => {
        const start = new Date(trip.start_time);
        const endStr = trip.end_time ? new Date(trip.end_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'Aktiv';
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>
            <div style="font-weight: 500;">${start.toLocaleDateString()}</div>
            <div style="font-size: 0.8rem; color: var(--text-secondary);">${start.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} - ${endStr}</div>
          </td>
          <td>
            <div style="font-weight: 500;">${trip.distance_km.toFixed(1)} km</div>
          </td>
          <td>
            <div style="font-weight: 500; color: #f59e0b;">${trip.battery_used_pct.toFixed(1)} %</div>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }
  } catch (err) {
    console.error('Failed to fetch trips:', err);
  }
}

// Initial fetch overrides
document.addEventListener('DOMContentLoaded', () => {
  fetchHistory(5);
  fetchTrips();
  // Polling slået fra
  // setInterval(fetchHistory, 5 * 60000); // 5 mins
  // setInterval(fetchTrips, 5 * 60000); // 5 mins
});
