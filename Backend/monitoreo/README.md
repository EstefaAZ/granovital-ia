# Modulo 03 - Monitoreo Ambiental y Suelo
## GranoVital IA - Trabajo de Grado

---

### Trazabilidad de Requisitos

| Requisito | Descripcion                              | Implementado en                          |
|-----------|------------------------------------------|------------------------------------------|
| RF-03     | Monitoreo ambiental del cultivo          | `services/monitoreo_service.py`          |
| RF-04     | Monitoreo del estado del suelo           | `services/monitoreo_service.py`          |
| RN-01     | Acceso por rol (RBAC)                    | `core/security.py` - `require_roles()`  |
| RN-03     | Datos validos para recomendaciones de IA | `verificar_validez_rn03()`               |
| RNF-09    | Interoperabilidad IoT via MQTT           | `mqtt_client.py`                         |
| RNF-10    | Operacion en zonas rurales               | Origen `manual` en todos los formularios |

---

### Estructura del Paquete

```
modulo_03_monitoreo/
  app/
    core/          config.py, database.py, security.py
    models/        monitoreo.py  (tbl_monitoreo_ambiental, tbl_monitoreo_suelo)
    schemas/       monitoreo.py  (validacion Pydantic con rangos agronomicos)
    services/      monitoreo_service.py  (logica de negocio y alertas)
    api/v1/        monitoreo.py  (8 endpoints REST)
    main.py        (punto de entrada FastAPI)
  frontend/src/
    pages/         Monitoreo.jsx  (dashboard principal)
    components/    FormularioAmbiental.jsx, FormularioSuelo.jsx
    hooks/         useMonitoreo.js  (polling automatico cada 60s)
    services/      monitoreoService.js  (cliente HTTP)
  tests/
    test_monitoreo.py  (45+ casos de prueba)
  mqtt_client.py   (suscriptor MQTT para ingesta IoT)
  requirements.txt
  .env.example
```

---

### Endpoints Disponibles

```
GET  /api/v1/monitoreo/{cultivo_id}/resumen       Dashboard consolidado
POST /api/v1/monitoreo/{cultivo_id}/ambiental     RF-03: registrar lectura ambiental
GET  /api/v1/monitoreo/{cultivo_id}/ambiental     RF-03: historial ambiental
GET  /api/v1/monitoreo/{cultivo_id}/ambiental/ultima  Ultima lectura ambiental
POST /api/v1/monitoreo/{cultivo_id}/suelo         RF-04: registrar lectura de suelo
GET  /api/v1/monitoreo/{cultivo_id}/suelo         RF-04: historial de suelo
GET  /api/v1/monitoreo/{cultivo_id}/suelo/ultima  Ultima lectura de suelo
GET  /api/v1/monitoreo/{cultivo_id}/validez       RN-03: verificar validez de datos
```

---

### Instalacion y Ejecucion

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Edite .env con sus valores reales

# 4. Iniciar servidor
uvicorn app.main:app --reload --port 8003

# 5. Ver documentacion interactiva
# http://localhost:8003/docs

# 6. Ejecutar pruebas unitarias
pytest tests/ -v

# 7. Iniciar cliente MQTT (opcional - requiere broker)
python mqtt_client.py
```

---

### Topics MQTT para Sensores IoT (RNF-09)

Los sensores deben publicar en formato JSON a los siguientes topics:

**Ambiental:**
```
Topic:   granovital/cultivo/{id_cultivo}/ambiental
Payload: {"temperatura": 22.5, "humedad_relativa": 78.0, "id_sensor": 1}
```

**Suelo:**
```
Topic:   granovital/cultivo/{id_cultivo}/suelo
Payload: {"ph": 6.2, "humedad_suelo": 55.0, "nitrogeno": 28.0, "id_sensor": 2}
```

---

### Rangos Agronomicos de Referencia (CENICAFE)

**Ambiente:**
- Temperatura optima: 18 a 24 C
- Humedad relativa optima: 70 a 90%
- Alerta temperatura: menor a 14 C o mayor a 30 C

**Suelo:**
- pH optimo para cafe: 5.5 a 6.5
- Nitrogeno minimo: 20 mg/kg
- Fosforo minimo: 15 mg/kg
- Potasio minimo: 20 mg/kg

---

### Dependencia con Otros Modulos

- **Modulo 01** - Autenticacion: provee el token JWT que este modulo valida.
- **Modulo 02** - Cultivos: el `cultivo_id` debe existir en `tbl_cultivo`.
- **Modulo 04** - IA: consulta `/validez` antes de generar recomendaciones (RN-03).
