import pandas as pd


def _split_codigo(texto: str):
    """'03495 - NOMBRE' -> ('03495', 'NOMBRE')"""
    if " - " in texto:
        cod, nom = texto.split(" - ", 1)
        return cod.strip(), nom.strip()
    return texto.strip(), ""


def parse_export(file):
    """Lee solo las columnas A-F (Group, Sucursal, Solicitado, Recibido,
    No Recibido, % Cumplimiento) del export jerárquico.

    Retorna (proveedores, estadisticos):
      - proveedores: una fila por proveedor (código de 4-5 dígitos)
      - estadisticos: una fila por producto (código de 9 dígitos) con su proveedor
    """
    raw = pd.read_excel(file, header=None, skiprows=2, usecols="A:F")
    raw.columns = ["group", "suc", "sol", "rec", "norec", "cumpl"]

    prov_rows, est_rows = [], []
    prov_cod = prov_nom = None
    for r in raw.itertuples(index=False):
        if not isinstance(r.group, str):
            continue  # filas por sucursal: se ignoran
        partes = [p.strip() for p in r.group.split("->") if p.strip()]
        nivel = len(partes)
        if nivel == 2:
            prov_cod, prov_nom = _split_codigo(partes[1])
            prov_rows.append((prov_cod, prov_nom, r.sol, r.rec, r.norec))
        elif nivel == 4:
            est_cod, est_nom = _split_codigo(partes[3])
            est_rows.append((est_cod, est_nom, prov_cod, prov_nom, r.sol, r.rec, r.norec))

    proveedores = pd.DataFrame(prov_rows, columns=[
        "Código", "Proveedor", "Solicitado", "Recibido", "No Recibido"])
    estadisticos = pd.DataFrame(est_rows, columns=[
        "Estadístico", "Descripción", "Cód. Proveedor", "Proveedor",
        "Solicitado", "Recibido", "No Recibido"])
    return proveedores, estadisticos
