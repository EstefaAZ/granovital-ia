// =============================================================
// frontend/src/pages/Register.jsx
// Página de registro multi-paso — GranoVital IA
// =============================================================

import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { authService } from "../services/authService";

const VERDE_CAFE = "#2D6A4F";
const CAFE = "#6B4226";
const GRIS_FONDO = "#F0F4F0";
const ROJO_ERROR = "#C73E1D";

const municipios = [
  "Armenia", "Calarcá", "Circasia", "Filandia", "Génova", "La Tebaida",
  "Montenegro", "Pijao", "Quimbaya", "Salento", "Apía", "Balboa",
  "Belalcázar", "Cáceres", "Cañasgordas", "Dagua", "El Águila", "El Cairo",
  "El Cerrito", "El Dovio", "El Peñol", "Florida", "Guacarí", "Guadalajara de Buga",
  "Jamundí", "La Cumbre", "La Unión", "La Victoria", "Obando", "Palmira",
  "Pradera", "Restrepo", "Riofrío", "Roldanillo", "San Pedro", "Sevilla",
  "Toro", "Trujillo", "Tuluá", "Ulloa", "Versalles", "Vijes", "Yotoco", "Zarzal"
];

const variedadesCafe = [
  "Caturra", "Catimor", "Colombia", "Typica", "Bourbon", "Geisha", "SL28", "SL34"
];

const paises = [
  "Colombia", "Estados Unidos", "México", "Canadá", "España", "Francia", "Italia",
  "Alemania", "Reino Unido", "Argentina", "Chile", "Perú", "Ecuador", "Brasil"
];

export default function Register() {
  const navigate = useNavigate();
  const [paso, setPaso] = useState(1);
  const [datos, setDatos] = useState({
    // Paso 1
    nombre: "",
    correo: "",
    contrasena: "",
    confirmarContrasena: "",
    telefono: "",
    tipoDocumento: "Cédula de ciudadanía",
    documento: "",
    municipio: "",
    // Paso 2
    rol: "",
    // Paso 3 - dependen del rol
    // Admin
    codigoAutorizacion: "",
    institucion: "",
    // Caficultor
    nombreFinca: "",
    vereda: "",
    areaCultivada: "",
    altitud: "",
    variedadPrincipal: "",
    sistemaCultivo: "",
    tipoProceso: "",
    unidadesPreferidas: "",
    canalAlertas: "",
    // Productor
    nombreFincaPlanta: "",
    veredaProductor: "",
    areaCultivadaProductor: "",
    altitudProductor: "",
    variedadPrincipalProductor: "",
    tiposProceso: [],
    prestaMaquila: "",
    unidadesPreferidasProductor: "",
    canalAlertasProductor: "",
    // Comercializador
    nombreEmpresa: "",
    nit: "",
    dv: "",
    tipoComercializador: "",
    regionInteres: "",
    preferenciaCalidad: "",
    // Consumidor
    apodo: "",
    paisResidencia: "",
    preferenciaCafe: "",
    // Paso 4
    aceptaTerminos: false,
    codigoVerificacion: "",
  });
  const [errores, setErrores] = useState({});
  const [cargando, setCargando] = useState(false);
  const [codigoEnviado, setCodigoEnviado] = useState(false);
  const [estadoCodigo, setEstadoCodigo] = useState(null);
  const [verificarEstadoInterval, setVerificarEstadoInterval] = useState(null);

  const actualizarDato = (campo, valor) => {
    setDatos(prev => ({ ...prev, [campo]: valor }));
    if (errores[campo]) {
      setErrores(prev => ({ ...prev, [campo]: "" }));
    }
  };

  const validarDocumentoTiempoReal = (valor) => {
    if (!valor.trim()) return "";

    if (datos.tipoDocumento === "Cédula de ciudadanía") {
      if (!/^\d{10}$/.test(valor)) {
        if (valor.length > 10) return "Máximo 10 dígitos";
        if (valor.length < 10) return `Faltan ${10 - valor.length} dígitos`;
        if (/[^0-9]/.test(valor)) return "Solo números permitidos";
      }
    } else if (datos.tipoDocumento === "Pasaporte") {
      if (!/^[A-Za-z0-9]{6,9}$/.test(valor)) {
        if (valor.length > 9) return "Máximo 9 caracteres";
        if (valor.length < 6) return `Mínimo 6 caracteres`;
        if (/[^A-Za-z0-9]/.test(valor)) return "Solo letras y números";
      }
    }
    return "";
  };

  const actualizarDocumento = (valor) => {
    // Validación en tiempo real para el campo documento
    let valorFiltrado = valor;

    if (datos.tipoDocumento === "Cédula de ciudadanía") {
      // Solo permitir números y máximo 10 dígitos
      valorFiltrado = valor.replace(/[^0-9]/g, '').substring(0, 10);
    } else if (datos.tipoDocumento === "Pasaporte") {
      // Solo permitir letras y números, máximo 9 caracteres
      valorFiltrado = valor.replace(/[^A-Za-z0-9]/g, '').substring(0, 9);
    }

    actualizarDato("documento", valorFiltrado);

    // Validar y mostrar errores en tiempo real
    const errorTiempoReal = validarDocumentoTiempoReal(valorFiltrado);
    if (errorTiempoReal) {
      setErrores(prev => ({ ...prev, documento: errorTiempoReal }));
    } else if (errores.documento && errores.documento !== "Documento es obligatorio") {
      setErrores(prev => ({ ...prev, documento: "" }));
    }
  };

  const cambiarTipoDocumento = (nuevoTipo) => {
    // Al cambiar el tipo de documento, validar si el documento actual es compatible
    const documentoActual = datos.documento;

    actualizarDato("tipoDocumento", nuevoTipo);

    // Si hay un documento actual, verificar si es válido para el nuevo tipo
    if (documentoActual) {
      let esValido = false;
      if (nuevoTipo === "Cédula de ciudadanía") {
        esValido = /^\d{10}$/.test(documentoActual);
      } else if (nuevoTipo === "Pasaporte") {
        esValido = /^[A-Za-z0-9]{6,9}$/.test(documentoActual);
      }

      // Si no es válido, limpiar el campo
      if (!esValido) {
        actualizarDato("documento", "");
      }
    }
  };

  const validarPaso1 = () => {
    const nuevosErrores = {};

    if (!datos.nombre.trim()) nuevosErrores.nombre = "Nombre completo es obligatorio";
    if (!datos.correo.trim()) {
      nuevosErrores.correo = "Correo electrónico es obligatorio";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(datos.correo)) {
      nuevosErrores.correo = "Correo electrónico inválido";
    }
    if (!datos.contrasena) {
      nuevosErrores.contrasena = "Contraseña es obligatoria";
    } else if (datos.contrasena.length < 8) {
      nuevosErrores.contrasena = "Contraseña debe tener al menos 8 caracteres";
    } else if (!/[A-Z]/.test(datos.contrasena) || !/\d/.test(datos.contrasena)) {
      nuevosErrores.contrasena = "Contraseña debe tener al menos una mayúscula y un número";
    }
    if (datos.contrasena !== datos.confirmarContrasena) {
      nuevosErrores.confirmarContrasena = "Las contraseñas no coinciden";
    }
    if (!datos.telefono.trim()) {
      nuevosErrores.telefono = "Teléfono es obligatorio";
    } else if (!/^\d{10}$/.test(datos.telefono)) {
      nuevosErrores.telefono = "Teléfono debe tener exactamente 10 dígitos";
    }
    if (!datos.documento.trim()) {
      nuevosErrores.documento = "Documento es obligatorio";
    } else if (datos.tipoDocumento === "Cédula de ciudadanía" && !/^\d{10}$/.test(datos.documento)) {
      nuevosErrores.documento = "Cédula debe tener exactamente 10 dígitos";
    } else if (datos.tipoDocumento === "Pasaporte" && !/^[A-Za-z0-9]{6,9}$/.test(datos.documento)) {
      nuevosErrores.documento = "Pasaporte debe tener 6-9 caracteres alfanuméricos";
    }
    if (!datos.municipio) nuevosErrores.municipio = "Municipio es obligatorio";

    setErrores(nuevosErrores);
    return Object.keys(nuevosErrores).length === 0;
  };

  const validarPaso2 = () => {
    if (!datos.rol) {
      setErrores({ rol: "Debe seleccionar un rol" });
      return false;
    }
    return true;
  };

  const validarPaso3 = () => {
    const nuevosErrores = {};

    if (datos.rol === "Administrador") {
      if (!datos.codigoAutorizacion.trim()) nuevosErrores.codigoAutorizacion = "Código de autorización es obligatorio";
      if (!datos.institucion.trim()) nuevosErrores.institucion = "Institución es obligatoria";
    } else if (datos.rol === "Caficultor") {
      if (!datos.nombreFinca.trim()) nuevosErrores.nombreFinca = "Nombre de la finca es obligatorio";
      if (!datos.vereda.trim()) nuevosErrores.vereda = "Vereda es obligatoria";
      if (!datos.areaCultivada || isNaN(datos.areaCultivada)) nuevosErrores.areaCultivada = "Área cultivada debe ser un número";
      if (!datos.variedadPrincipal) nuevosErrores.variedadPrincipal = "Variedad principal es obligatoria";
      if (!datos.sistemaCultivo) nuevosErrores.sistemaCultivo = "Sistema de cultivo es obligatorio";
      if (!datos.tipoProceso) nuevosErrores.tipoProceso = "Tipo de proceso es obligatorio";
      if (!datos.unidadesPreferidas) nuevosErrores.unidadesPreferidas = "Unidades preferidas es obligatorio";
      if (!datos.canalAlertas) nuevosErrores.canalAlertas = "Canal de alertas es obligatorio";
    } else if (datos.rol === "Productor") {
      if (!datos.nombreFincaPlanta.trim()) nuevosErrores.nombreFincaPlanta = "Nombre de la finca/planta es obligatorio";
      if (!datos.veredaProductor.trim()) nuevosErrores.veredaProductor = "Vereda es obligatoria";
      if (!datos.areaCultivadaProductor || isNaN(datos.areaCultivadaProductor)) nuevosErrores.areaCultivadaProductor = "Área cultivada debe ser un número";
      if (!datos.variedadPrincipalProductor) nuevosErrores.variedadPrincipalProductor = "Variedad principal es obligatoria";
      if (datos.tiposProceso.length === 0) nuevosErrores.tiposProceso = "Debe seleccionar al menos un tipo de proceso";
      if (!datos.prestaMaquila) nuevosErrores.prestaMaquila = "Debe indicar si presta servicios de maquila";
      if (!datos.unidadesPreferidasProductor) nuevosErrores.unidadesPreferidasProductor = "Unidades preferidas es obligatorio";
      if (!datos.canalAlertasProductor) nuevosErrores.canalAlertasProductor = "Canal de alertas es obligatorio";
    } else if (datos.rol === "Comercializador") {
      if (!datos.nombreEmpresa.trim()) nuevosErrores.nombreEmpresa = "Nombre de empresa es obligatorio";
      if (!datos.nit.trim()) {
        nuevosErrores.nit = "NIT es obligatorio";
      } else if (!/^\d{9}$/.test(datos.nit)) {
        nuevosErrores.nit = "NIT debe tener exactamente 9 dígitos";
      }
      if (!datos.dv || !/^\d$/.test(datos.dv)) nuevosErrores.dv = "Dígito de verificación debe ser un número";
      if (!datos.tipoComercializador) nuevosErrores.tipoComercializador = "Tipo de comercializador es obligatorio";
      if (!datos.regionInteres) nuevosErrores.regionInteres = "Región de interés es obligatoria";
    } else if (datos.rol === "Consumidor") {
      if (!datos.apodo.trim()) nuevosErrores.apodo = "Apodo es obligatorio";
      if (!datos.paisResidencia) nuevosErrores.paisResidencia = "País de residencia es obligatorio";
      if (!datos.preferenciaCafe) nuevosErrores.preferenciaCafe = "Preferencia de café es obligatoria";
    }

    setErrores(nuevosErrores);
    return Object.keys(nuevosErrores).length === 0;
  };

  const validarPaso4 = () => {
    const nuevosErrores = {};
    if (!datos.aceptaTerminos) nuevosErrores.aceptaTerminos = "Debe aceptar los términos y política de datos";
    if (!codigoEnviado) {
      nuevosErrores.general = "Debe enviar el código de verificación primero";
    } else if (!datos.codigoVerificacion.trim()) {
      nuevosErrores.codigoVerificacion = "Código de verificación es obligatorio";
    }
    setErrores(nuevosErrores);
    return Object.keys(nuevosErrores).length === 0;
  };

  const verificarEstadoCodigo = async () => {
    if (!datos.correo.trim()) return;

    try {
      const estado = await authService.verificarEstadoCodigo(datos.correo);
      setEstadoCodigo(estado);
    } catch (error) {
      console.warn("Error verificando estado del código:", error);
      setEstadoCodigo(null);
    }
  };

  const enviarCodigo = async () => {
    if (!datos.correo.trim()) {
      setErrores({ general: "Ingrese su correo electrónico primero" });
      return;
    }

    setCargando(true);
    try {
      await authService.enviarCodigoVerificacion(datos.correo);
      setCodigoEnviado(true);
      setErrores({});

      // Iniciar verificación periódica del estado
      verificarEstadoCodigo();
      const interval = setInterval(verificarEstadoCodigo, 5000); // Cada 5 segundos
      setVerificarEstadoInterval(interval);

    } catch (error) {
      setErrores({ general: error.message });
    } finally {
      setCargando(false);
    }
  };

  const siguientePaso = () => {
    let valido = false;
    if (paso === 1) valido = validarPaso1();
    else if (paso === 2) valido = validarPaso2();
    else if (paso === 3) valido = validarPaso3();
    if (valido) setPaso(paso + 1);
  };

  const pasoAnterior = () => setPaso(paso - 1);

  const registrar = async () => {
    if (!validarPaso4()) return;

    setCargando(true);
    try {
      const datosRegistro = {
        ...datos,
        telefono: datos.telefono,
        documento: datos.documento,
      };
      await authService.registrar(datosRegistro);
      // Redirigir al login o directamente loguear
      navigate("/login");
    } catch (error) {
      setErrores({ general: error.message || "Error en el registro" });
    } finally {
      setCargando(false);
    }
  };

  // Cleanup del interval cuando el componente se desmonte
  React.useEffect(() => {
    return () => {
      if (verificarEstadoInterval) {
        clearInterval(verificarEstadoInterval);
      }
    };
  }, [verificarEstadoInterval]);

  const renderPaso1 = () => (
    <div>
      <h3 style={styles.tituloPaso}>Paso 1 — Datos personales</h3>
      <CampoTexto label="Nombre completo" value={datos.nombre} onChange={v => actualizarDato("nombre", v)} error={errores.nombre} />
      <CampoTexto label="Correo electrónico" type="email" value={datos.correo} onChange={v => actualizarDato("correo", v)} error={errores.correo} />
      <CampoTexto label="Contraseña" type="password" value={datos.contrasena} onChange={v => actualizarDato("contrasena", v)} error={errores.contrasena} />
      <CampoTexto label="Confirmar contraseña" type="password" value={datos.confirmarContrasena} onChange={v => actualizarDato("confirmarContrasena", v)} error={errores.confirmarContrasena} />
      <CampoTexto label="Teléfono / WhatsApp" value={datos.telefono} onChange={v => actualizarDato("telefono", v)} error={errores.telefono} placeholder="3001234567" />
      <div style={styles.grupo}>
        <label style={styles.etiqueta}>Tipo de documento</label>
        <select value={datos.tipoDocumento} onChange={e => cambiarTipoDocumento(e.target.value)} style={styles.select}>
          <option value="Cédula de ciudadanía">Cédula de ciudadanía</option>
          <option value="Pasaporte">Pasaporte</option>
        </select>
      </div>
      <CampoTexto
        label="Documento de identidad"
        value={datos.documento}
        onChange={actualizarDocumento}
        error={errores.documento}
        placeholder={datos.tipoDocumento === "Cédula de ciudadanía" ? "1234567890 (10 dígitos)" : "ABC123456 (6-9 caracteres)"}
      />
      <div style={{
        fontSize: '12px',
        color: datos.documento && !errores.documento && (
          (datos.tipoDocumento === "Cédula de ciudadanía" && /^\d{10}$/.test(datos.documento)) ||
          (datos.tipoDocumento === "Pasaporte" && /^[A-Za-z0-9]{6,9}$/.test(datos.documento))
        ) ? '#2D6A4F' : '#666',
        marginTop: '5px'
      }}>
        {datos.documento && !errores.documento && (
          (datos.tipoDocumento === "Cédula de ciudadanía" && /^\d{10}$/.test(datos.documento)) ||
          (datos.tipoDocumento === "Pasaporte" && /^[A-Za-z0-9]{6,9}$/.test(datos.documento))
        ) ? (
          <span>✅ Documento válido</span>
        ) : (
          <span>
            {datos.tipoDocumento === "Cédula de ciudadanía"
              ? "Solo números, exactamente 10 dígitos"
              : "Letras y números, entre 6 y 9 caracteres"
            }
          </span>
        )}
      </div>
      <div style={styles.grupo}>
        <label style={styles.etiqueta}>Municipio</label>
        <select value={datos.municipio} onChange={e => actualizarDato("municipio", e.target.value)} style={styles.select}>
          <option value="">Seleccionar municipio</option>
          {municipios.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        {errores.municipio && <span style={styles.mensajeError}>{errores.municipio}</span>}
      </div>
    </div>
  );

  const renderPaso2 = () => (
    <div>
      <h3 style={styles.tituloPaso}>Paso 2 — Selección de rol</h3>
      <div style={styles.rolesGrid}>
        {["Administrador", "Caficultor", "Productor", "Comercializador", "Consumidor"].map(rol => (
          <button
            key={rol}
            type="button"
            onClick={() => actualizarDato("rol", rol)}
            style={{
              ...styles.rolButton,
              ...(datos.rol === rol ? styles.rolButtonActive : {}),
            }}
          >
            {rol}
          </button>
        ))}
      </div>
      {errores.rol && <span style={styles.mensajeError}>{errores.rol}</span>}
    </div>
  );

  const renderPaso3 = () => {
    if (datos.rol === "Administrador") {
      return (
        <div>
          <h3 style={styles.tituloPaso}>Paso 3 — Datos de Administrador</h3>
          <CampoTexto label="Código de autorización" value={datos.codigoAutorizacion} onChange={v => actualizarDato("codigoAutorizacion", v)} error={errores.codigoAutorizacion} />
          <CampoTexto label="Institución o dependencia" value={datos.institucion} onChange={v => actualizarDato("institucion", v)} error={errores.institucion} />
        </div>
      );
    } else if (datos.rol === "Caficultor") {
      return (
        <div>
          <h3 style={styles.tituloPaso}>Paso 3 — Datos de Caficultor</h3>
          <CampoTexto label="Nombre de la finca" value={datos.nombreFinca} onChange={v => actualizarDato("nombreFinca", v)} error={errores.nombreFinca} />
          <CampoTexto label="Vereda o corregimiento" value={datos.vereda} onChange={v => actualizarDato("vereda", v)} error={errores.vereda} />
          <CampoTexto label="Área cultivada en hectáreas" type="number" value={datos.areaCultivada} onChange={v => actualizarDato("areaCultivada", v)} error={errores.areaCultivada} />
          <CampoTexto label="Altitud en msnm (opcional)" type="number" value={datos.altitud} onChange={v => actualizarDato("altitud", v)} />
          <CampoSelect label="Variedad principal de café" options={variedadesCafe} value={datos.variedadPrincipal} onChange={v => actualizarDato("variedadPrincipal", v)} error={errores.variedadPrincipal} />
          <CampoSelect label="Sistema de cultivo" options={["tecnificado", "semitecnificado", "tradicional"]} value={datos.sistemaCultivo} onChange={v => actualizarDato("sistemaCultivo", v)} error={errores.sistemaCultivo} />
          <CampoSelect label="Tipo de proceso postcosecha" options={["lavado", "natural", "honey"]} value={datos.tipoProceso} onChange={v => actualizarDato("tipoProceso", v)} error={errores.tipoProceso} />
          <CampoSelect label="Unidades preferidas" options={["kg", "arrobas", "quintales"]} value={datos.unidadesPreferidas} onChange={v => actualizarDato("unidadesPreferidas", v)} error={errores.unidadesPreferidas} />
          <CampoSelect label="Canal de alertas" options={["WhatsApp", "correo"]} value={datos.canalAlertas} onChange={v => actualizarDato("canalAlertas", v)} error={errores.canalAlertas} />
        </div>
      );
    } else if (datos.rol === "Productor") {
      return (
        <div>
          <h3 style={styles.tituloPaso}>Paso 3 — Datos de Productor</h3>
          <CampoTexto label="Nombre de la finca o planta de beneficio" value={datos.nombreFincaPlanta} onChange={v => actualizarDato("nombreFincaPlanta", v)} error={errores.nombreFincaPlanta} />
          <CampoTexto label="Vereda o corregimiento" value={datos.veredaProductor} onChange={v => actualizarDato("veredaProductor", v)} error={errores.veredaProductor} />
          <CampoTexto label="Área cultivada en hectáreas" type="number" value={datos.areaCultivadaProductor} onChange={v => actualizarDato("areaCultivadaProductor", v)} error={errores.areaCultivadaProductor} />
          <CampoTexto label="Altitud en msnm (opcional)" type="number" value={datos.altitudProductor} onChange={v => actualizarDato("altitudProductor", v)} />
          <CampoSelect label="Variedad principal de café" options={variedadesCafe} value={datos.variedadPrincipalProductor} onChange={v => actualizarDato("variedadPrincipalProductor", v)} error={errores.variedadPrincipalProductor} />
          <div style={styles.grupo}>
            <label style={styles.etiqueta}>Tipos de proceso que maneja</label>
            <div style={styles.checkboxGroup}>
              {["lavado", "natural", "honey"].map(proceso => (
                <label key={proceso} style={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={datos.tiposProceso.includes(proceso)}
                    onChange={e => {
                      const nuevos = e.target.checked
                        ? [...datos.tiposProceso, proceso]
                        : datos.tiposProceso.filter(p => p !== proceso);
                      actualizarDato("tiposProceso", nuevos);
                    }}
                  />
                  {proceso}
                </label>
              ))}
            </div>
            {errores.tiposProceso && <span style={styles.mensajeError}>{errores.tiposProceso}</span>}
          </div>
          <CampoSelect label="¿Presta servicios de maquila?" options={["Sí", "No"]} value={datos.prestaMaquila} onChange={v => actualizarDato("prestaMaquila", v)} error={errores.prestaMaquila} />
          <CampoSelect label="Unidades preferidas" options={["kg", "arrobas", "quintales"]} value={datos.unidadesPreferidasProductor} onChange={v => actualizarDato("unidadesPreferidasProductor", v)} error={errores.unidadesPreferidasProductor} />
          <CampoSelect label="Canal de alertas" options={["WhatsApp", "correo"]} value={datos.canalAlertasProductor} onChange={v => actualizarDato("canalAlertasProductor", v)} error={errores.canalAlertasProductor} />
        </div>
      );
    } else if (datos.rol === "Comercializador") {
      return (
        <div>
          <h3 style={styles.tituloPaso}>Paso 3 — Datos de Comercializador</h3>
          <CampoTexto label="Nombre de empresa u organización" value={datos.nombreEmpresa} onChange={v => actualizarDato("nombreEmpresa", v)} error={errores.nombreEmpresa} />
          <div style={styles.grupo}>
            <label style={styles.etiqueta}>NIT</label>
            <div style={styles.nitContainer}>
              <input
                type="text"
                value={datos.nit}
                onChange={e => actualizarDato("nit", e.target.value.replace(/\D/g, '').slice(0, 9))}
                style={styles.input}
                placeholder="123456789"
              />
              <span style={styles.nitSeparator}>-</span>
              <input
                type="text"
                value={datos.dv}
                onChange={e => actualizarDato("dv", e.target.value.replace(/\D/g, '').slice(0, 1))}
                style={{ ...styles.input, width: "40px" }}
                placeholder="5"
              />
            </div>
            {errores.nit && <span style={styles.mensajeError}>{errores.nit}</span>}
            {errores.dv && <span style={styles.mensajeError}>{errores.dv}</span>}
          </div>
          <CampoSelect label="Tipo de comercializador" options={["exportador", "tostador", "intermediario", "cooperativa"]} value={datos.tipoComercializador} onChange={v => actualizarDato("tipoComercializador", v)} error={errores.tipoComercializador} />
          <CampoSelect label="Región de interés de compra" options={municipios} value={datos.regionInteres} onChange={v => actualizarDato("regionInteres", v)} error={errores.regionInteres} />
          <CampoTexto label="Preferencia de calidad o proceso (opcional)" value={datos.preferenciaCalidad} onChange={v => actualizarDato("preferenciaCalidad", v)} />
        </div>
      );
    } else if (datos.rol === "Consumidor") {
      return (
        <div>
          <h3 style={styles.tituloPaso}>Paso 3 — Datos de Consumidor</h3>
          <CampoTexto label="Apodo o nombre público" value={datos.apodo} onChange={v => actualizarDato("apodo", v)} error={errores.apodo} />
          <CampoSelect label="País de residencia" options={paises} value={datos.paisResidencia} onChange={v => actualizarDato("paisResidencia", v)} error={errores.paisResidencia} />
          <CampoSelect label="Preferencia de café" options={["origen", "proceso", "variedad"]} value={datos.preferenciaCafe} onChange={v => actualizarDato("preferenciaCafe", v)} error={errores.preferenciaCafe} />
        </div>
      );
    }
    return null;
  };

  const renderPaso4 = () => (
    <div>
      <h3 style={styles.tituloPaso}>Paso 4 — Confirmación</h3>
      <div style={styles.grupo}>
        <label style={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={datos.aceptaTerminos}
            onChange={e => actualizarDato("aceptaTerminos", e.target.checked)}
          />
          Acepto los términos y condiciones y la política de datos
        </label>
        {errores.aceptaTerminos && <span style={styles.mensajeError}>{errores.aceptaTerminos}</span>}
      </div>
      <div style={styles.grupo}>
        <button type="button" onClick={enviarCodigo} disabled={cargando || codigoEnviado} style={styles.botonSecundario}>
          {codigoEnviado ? "Código enviado" : "Enviar código de verificación"}
        </button>
        {estadoCodigo && (
          <div style={{ marginTop: '10px', fontSize: '14px', color: '#666' }}>
            {estadoCodigo.has_active_code ? (
              <span style={{ color: '#2D6A4F' }}>
                ✅ Código activo - Expira en {Math.floor(estadoCodigo.expires_in_seconds / 60)} minutos
                {estadoCodigo.attempts > 0 && ` (${estadoCodigo.attempts} intentos fallidos)`}
              </span>
            ) : (
              <span style={{ color: '#C73E1D' }}>
                ❌ No hay código activo
              </span>
            )}
          </div>
        )}
      </div>
      <CampoTexto label="Código de verificación" value={datos.codigoVerificacion} onChange={v => actualizarDato("codigoVerificacion", v)} error={errores.codigoVerificacion} />
      {errores.general && <div style={styles.alertaError}>{errores.general}</div>}
    </div>
  );

  return (
    <div style={styles.pagina}>
      <div style={styles.fondo} aria-hidden="true" />
      <div style={styles.contenedor}>
        <div style={styles.encabezado}>
          <div style={styles.logoIcono} aria-label="Logo GranoVital IA">☕</div>
          <h1 style={styles.titulo}>GranoVital IA</h1>
          <p style={styles.subtitulo}>Crear cuenta</p>
        </div>

        <div style={styles.tarjeta}>
          <div style={styles.progreso}>
            {[1, 2, 3, 4].map(p => (
              <div key={p} style={{
                ...styles.pasoCirculo,
                ...(p <= paso ? styles.pasoCirculoActivo : {}),
              }}>
                {p}
              </div>
            ))}
          </div>

          {paso === 1 && renderPaso1()}
          {paso === 2 && renderPaso2()}
          {paso === 3 && renderPaso3()}
          {paso === 4 && renderPaso4()}

          <div style={styles.botonesNavegacion}>
            {paso > 1 && (
              <button type="button" onClick={pasoAnterior} style={styles.botonAnterior}>
                Anterior
              </button>
            )}
            {paso < 4 ? (
              <button type="button" onClick={siguientePaso} style={styles.botonSiguiente}>
                Siguiente
              </button>
            ) : (
              <button type="button" onClick={registrar} disabled={cargando} style={styles.botonPrincipal}>
                {cargando ? "Registrando..." : "Crear cuenta"}
              </button>
            )}
          </div>

          <div style={styles.loginLink}>
            <p>¿Ya tienes cuenta? <button onClick={() => navigate("/login")} style={styles.link}>Iniciar sesión</button></p>
          </div>
        </div>

        <p style={styles.footer}>
          Universidad Católica Luis Amigó · GranoVital IA v1.0
        </p>
      </div>
    </div>
  );
}

const CampoTexto = ({ label, type = "text", value, onChange, error, placeholder }) => (
  <div style={styles.grupo}>
    <label style={styles.etiqueta}>{label}</label>
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      style={{
        ...styles.input,
        ...(error ? styles.inputError : {}),
      }}
    />
    {error && <span style={styles.mensajeError}>{error}</span>}
  </div>
);

const CampoSelect = ({ label, options, value, onChange, error }) => (
  <div style={styles.grupo}>
    <label style={styles.etiqueta}>{label}</label>
    <select value={value} onChange={e => onChange(e.target.value)} style={styles.select}>
      <option value="">Seleccionar</option>
      {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
    </select>
    {error && <span style={styles.mensajeError}>{error}</span>}
  </div>
);

const styles = {
  pagina: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: GRIS_FONDO,
    fontFamily: "'Segoe UI', Arial, sans-serif",
    padding: "20px",
    position: "relative",
    overflow: "hidden",
  },
  fondo: {
    position: "absolute",
    top: 0, left: 0, right: 0, bottom: 0,
    background: `linear-gradient(135deg, ${VERDE_CAFE}22 0%, ${CAFE}11 100%)`,
    pointerEvents: "none",
  },
  contenedor: {
    width: "100%",
    maxWidth: "600px",
    position: "relative",
    zIndex: 1,
  },
  encabezado: {
    textAlign: "center",
    marginBottom: "24px",
  },
  logoIcono: {
    fontSize: "52px",
    display: "block",
    marginBottom: "8px",
    filter: "drop-shadow(0 4px 8px rgba(0,0,0,0.15))",
  },
  titulo: {
    fontSize: "28px",
    fontWeight: "800",
    color: VERDE_CAFE,
    margin: "0 0 4px 0",
    letterSpacing: "-0.5px",
  },
  subtitulo: {
    fontSize: "14px",
    color: "#666",
    margin: 0,
  },
  tarjeta: {
    backgroundColor: "white",
    borderRadius: "16px",
    padding: "36px 40px",
    boxShadow: "0 4px 24px rgba(0,0,0,0.10), 0 1px 4px rgba(0,0,0,0.06)",
  },
  progreso: {
    display: "flex",
    justifyContent: "center",
    gap: "16px",
    marginBottom: "32px",
  },
  pasoCirculo: {
    width: "40px",
    height: "40px",
    borderRadius: "50%",
    border: `2px solid #DDD`,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: "600",
    color: "#999",
    backgroundColor: "#F9F9F9",
  },
  pasoCirculoActivo: {
    backgroundColor: VERDE_CAFE,
    color: "white",
    borderColor: VERDE_CAFE,
  },
  tituloPaso: {
    fontSize: "18px",
    fontWeight: "700",
    color: "#1A1A1A",
    margin: "0 0 24px 0",
  },
  grupo: {
    marginBottom: "20px",
  },
  etiqueta: {
    display: "block",
    fontSize: "13px",
    fontWeight: "600",
    color: "#333",
    marginBottom: "6px",
  },
  input: {
    width: "100%",
    padding: "11px 14px",
    fontSize: "15px",
    border: "1.5px solid #DDD",
    borderRadius: "8px",
    outline: "none",
    transition: "border-color 0.2s",
    boxSizing: "border-box",
    backgroundColor: "#FAFAFA",
    color: "#1A1A1A",
  },
  inputError: {
    borderColor: ROJO_ERROR,
    backgroundColor: "#FFF8F8",
  },
  select: {
    width: "100%",
    padding: "11px 14px",
    fontSize: "15px",
    border: "1.5px solid #DDD",
    borderRadius: "8px",
    outline: "none",
    transition: "border-color 0.2s",
    boxSizing: "border-box",
    backgroundColor: "#FAFAFA",
    color: "#1A1A1A",
  },
  mensajeError: {
    display: "block",
    fontSize: "12px",
    color: ROJO_ERROR,
    fontWeight: "500",
    marginTop: "4px",
  },
  rolesGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
    gap: "12px",
    marginBottom: "20px",
  },
  rolButton: {
    padding: "16px 12px",
    border: "2px solid #DDD",
    borderRadius: "8px",
    backgroundColor: "white",
    color: "#333",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    transition: "all 0.2s",
    textAlign: "center",
  },
  rolButtonActive: {
    borderColor: VERDE_CAFE,
    backgroundColor: `${VERDE_CAFE}10`,
    color: VERDE_CAFE,
  },
  checkboxGroup: {
    display: "flex",
    flexWrap: "wrap",
    gap: "12px",
  },
  checkboxLabel: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    fontSize: "14px",
    color: "#333",
  },
  nitContainer: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  nitSeparator: {
    fontSize: "18px",
    fontWeight: "600",
    color: "#333",
  },
  botonesNavegacion: {
    display: "flex",
    justifyContent: "space-between",
    marginTop: "32px",
  },
  botonAnterior: {
    padding: "12px 24px",
    backgroundColor: "#F0F0F0",
    color: "#333",
    border: "none",
    borderRadius: "8px",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    transition: "background-color 0.2s",
  },
  botonSiguiente: {
    padding: "12px 24px",
    backgroundColor: VERDE_CAFE,
    color: "white",
    border: "none",
    borderRadius: "8px",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    transition: "background-color 0.2s",
  },
  botonPrincipal: {
    padding: "12px 24px",
    backgroundColor: VERDE_CAFE,
    color: "white",
    border: "none",
    borderRadius: "8px",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    transition: "background-color 0.2s",
  },
  botonSecundario: {
    padding: "10px 20px",
    backgroundColor: "transparent",
    color: VERDE_CAFE,
    border: `1px solid ${VERDE_CAFE}`,
    borderRadius: "8px",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    transition: "all 0.2s",
  },
  alertaError: {
    backgroundColor: "#FEF2F2",
    border: `1px solid ${ROJO_ERROR}44`,
    borderRadius: "8px",
    padding: "12px 16px",
    marginBottom: "20px",
    fontSize: "13px",
    color: ROJO_ERROR,
    lineHeight: "1.5",
  },
  loginLink: {
    textAlign: "center",
    marginTop: "24px",
    paddingTop: "20px",
    borderTop: "1px solid #F0F0F0",
  },
  link: {
    background: "none",
    border: "none",
    color: VERDE_CAFE,
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: "600",
    textDecoration: "underline",
  },
  footer: {
    textAlign: "center",
    fontSize: "11px",
    color: "#AAA",
    marginTop: "20px",
  },
};