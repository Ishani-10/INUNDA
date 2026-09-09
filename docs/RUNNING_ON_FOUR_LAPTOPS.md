# Running the INUNDA demo across four laptops

Same pattern as POLARIS. One machine hosts the backend + frontend; the others connect over the LAN.

## Host (Laptop 2)
```bash
# backend
cd Inunda/backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# frontend (second terminal)
cd Inunda/frontend
npm install && npm run build && npm run dev
```
Find the host IP:
```bash
ipconfig getifaddr en0   # or en1 on some Macs
```
(e.g. `192.168.43.27`)

## Other laptops (same Wi-Fi / hotspot)
- Laptop 3 (Nowcast): http://192.168.43.27:5173/
- Laptop 4 (Routes): http://192.168.43.27:5173/ (switch tab to Flood-Safe Routes)
- API docs: http://192.168.43.27:8000/docs

> College Wi-Fi often blocks device-to-device traffic → use a private phone hotspot or a travel router so all four see each other.

## One-laptop fallback
```
http://localhost:5173/
http://localhost:8000/docs
```

## Notes
- The frontend proxies `/api` to `http://127.0.0.1:8000` (local). For LAN access the backend is already bound to `0.0.0.0`, so other laptops hit port 8000 directly for the API and port 5173 for the UI.
- Use the browser tabs to switch Nowcast / Flood-Safe Routes / ML Model on the showing laptop.
