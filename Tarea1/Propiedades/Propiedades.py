from CoolProp.CoolProp import PropsSI

def propiedades_aire(T, P):
    """
    Calcula propiedades del aire dado un estado (T, P).
    T: temperatura [K]
    P: presión [Pa]
    """
    return {
        "Densidad [kg/m3]":            PropsSI("D", "T", T, "P", P, "Air"),
        "Cp [J/kg-K]":                 PropsSI("C", "T", T, "P", P, "Air"),
        "Cv [J/kg-K]":                 PropsSI("CVMASS", "T", T, "P", P, "Air"),
        "Conductividad térm. [W/m-K]": PropsSI("L", "T", T, "P", P, "Air"),
        "Viscosidad dinám. [Pa-s]":    PropsSI("V", "T", T, "P", P, "Air"),
        "Entalpía [J/kg]":             PropsSI("H", "T", T, "P", P, "Air"),
        "Entropía [J/kg-K]":           PropsSI("S", "T", T, "P", P, "Air"),
        "Vel. del sonido [m/s]":       PropsSI("A", "T", T, "P", P, "Air"),
    }

if __name__ == "__main__":
    T = float(input("Temperatura [K]: "))
    P = float(input("Presión [Pa]: "))
    for nombre, valor in propiedades_aire(T, P).items():
        print(f"{nombre}: {valor:,.10e}")