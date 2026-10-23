import pandas as pd

BODEGAS = {
    "100": "100 - CND Lomas de Sargentillo",
    "200": "200 - CRD Calacali",
}


def nombre_bodega(codigo: str) -> str:
    return BODEGAS.get(codigo, f"{codigo} - Otra bodega")


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
      - proveedores: una fila por proveedor (total)
      - estadisticos: una fila por producto (código de 9 dígitos) y bodega
    """
    raw = pd.read_excel(file, header=None, skiprows=2, usecols="A:F")
    raw.columns = ["group", "suc", "sol", "rec", "norec", "cumpl"]

    prov_rows, est_rows = [], []
    prov_cod = prov_nom = est_cod = est_nom = None
    for r in raw.itertuples(index=False):
        if isinstance(r.group, str):
            partes = [p.strip() for p in r.group.split("->") if p.strip()]
            nivel = len(partes)
            if nivel == 2:
                prov_cod, prov_nom = _split_codigo(partes[1])
                est_cod = None
                prov_rows.append((prov_cod, prov_nom, r.sol, r.rec, r.norec))
            elif nivel == 4:
                est_cod, est_nom = _split_codigo(partes[3])
        elif pd.notna(r.suc) and est_cod is not None:
            bod = str(int(r.suc))
            est_rows.append((est_cod, est_nom, prov_cod, prov_nom,
                             nombre_bodega(bod), r.sol, r.rec, r.norec))

    proveedores = pd.DataFrame(prov_rows, columns=[
        "Código", "Proveedor", "Solicitado", "Recibido", "No Recibido"])
    estadisticos = pd.DataFrame(est_rows, columns=[
        "Estadístico", "Descripción", "Cód. Proveedor", "Proveedor", "Bodega",
        "Solicitado", "Recibido", "No Recibido"])
    return proveedores, estadisticos
