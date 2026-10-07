"""
Notificaciones de Windows (las del centro de notificaciones), sin internet ni dependencias: un PowerShell sin
ventana que muestra un aviso con la API de Windows. Lo usan el lanzador (iniciar_cacao.py: Cacao se cerró por un
error, ya está en marcha, faltan archivos) y quien necesite avisar sin terminal.
"""
import html
import subprocess

CREATE_NO_WINDOW = 0x0800_0000
# El aviso sale a nombre de Windows PowerShell (su AppUserModelID viene registrado en Windows).
APP = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe"


def script(titulo, texto):
    def xml(t):
        return html.escape(t, quote=True).replace("'", "''")  # comillas simples: van dentro de '...' de PowerShell
    return (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]"
        " > $null; "
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null; "
        "$x = New-Object Windows.Data.Xml.Dom.XmlDocument; "
        f"$x.LoadXml('<toast><visual><binding template=\"ToastGeneric\"><text>{xml(titulo)}</text>"
        f"<text>{xml(texto)}</text></binding></visual></toast>'); "
        f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{APP}')"
        ".Show([Windows.UI.Notifications.ToastNotification]::new($x))")


def notificar(titulo, texto, ejecutar=subprocess.run):
    """Muestra el aviso. True si PowerShell no dio error (no garantiza que Windows lo enseñe: el modo «No
    molestar» lo deja en el centro de notificaciones)."""
    try:
        r = ejecutar(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script(titulo, texto)],
                     capture_output=True, timeout=30, creationflags=CREATE_NO_WINDOW)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
