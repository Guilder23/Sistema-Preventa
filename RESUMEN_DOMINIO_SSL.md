# Resumen de configuración de dominio y SSL

Este archivo recoge de forma explicada qué se hizo para dejar funcionando el dominio en el servidor y habilitar HTTPS.

## 1. Objetivo

Se quería usar el dominio `distribuidorajeremy.duckdns.org` para apuntar al sistema oficial `SistemaPreventaOficial` y que el sitio no mostrara advertencia de inseguridad.

## 2. Verificación del servidor

Se conectó al servidor remoto por SSH con el usuario root y la IP `187.127.45.61`.

- Esto permitió entrar a la máquina donde está desplegado el sistema.
- Se revisó si Nginx y Gunicorn estaban activos, porque el sitio se sirve a través de Nginx y Django corre detrás de Gunicorn.

## 3. Configuración del dominio en Nginx

Se editó la configuración del sitio en Nginx para que el servidor reconociera el nuevo nombre de dominio.

- Se modificó el bloque `server_name` del sitio oficial.
- Antes solo estaba escuchando la IP pública y algunos hosts localhost.
- Ahora se incluyeron los nombres:
  - `distribuidorajeremy.duckdns.org`
  - `www.distribuidorajeremy.duckdns.org`

Esto hace que Nginx sepa qué sitio responder cuando alguien entra por ese dominio.

## 4. Ajuste de Django para hosts permitidos

Django tiene una configuración llamada `ALLOWED_HOSTS`, que define qué dominios pueden servir la aplicación sin bloquear la solicitud.

- Se añadió el dominio nuevo a esa lista.
- Si no se hubiera hecho, Django podía devolver error de host no permitido aunque Nginx sí lo dirigiera correctamente.

## 5. Why se usó el correo electrónico

Se usó un correo electrónico al generar el certificado SSL porque Certbot lo solicita para:

- registrar la cuenta de Let's Encrypt,
- enviar avisos importantes sobre renovación o problemas de seguridad,
- identificar el propietario del certificado.

El correo usado fue `paredesguilder36@gmail.com`.

## 6. Instalación de SSL con Certbot

Se instaló Certbot y se generó un certificado SSL para el dominio usando Nginx.

- `certbot` es la herramienta recomendada para obtener certificados gratuitos de Let's Encrypt.
- `python3-certbot-nginx` permite integrarlo fácilmente con Nginx.
- El certificado se emitió para:
  - `distribuidorajeremy.duckdns.org`
  - `www.distribuidorajeremy.duckdns.org`

## 7. Problema encontrado con el primer intento

Al emitir el certificado, Certbot intentó incluir también `www.187.127.45.61`, que no es un dominio público válido.

- Eso provocó un error de Let’s Encrypt.
- Se corrigió la configuración de Nginx para que solo se usaran los nombres públicos válidos.

## 8. Resultado final

Después de aplicar los cambios:

- Nginx quedó configurado para atender el dominio.
- Django aceptó el dominio.
- Certbot generó el certificado SSL.
- El sitio quedó accesible con HTTPS.

## 9. Cómo mover o repetir este cambio

Si se quiere hacer este cambio en otro servidor o volver a configurarlo más tarde, los pasos principales son:

1. Conectarse al servidor por SSH.
2. Verificar que Nginx y Gunicorn estén corriendo.
3. Editar el bloque del sitio en `/etc/nginx/sites-available/sistema-preventa`.
4. Añadir el dominio en `server_name`.
5. Añadir el dominio en `ALLOWED_HOSTS` del proyecto Django.
6. Ejecutar `nginx -t` para comprobar sintaxis.
7. Recargar Nginx.
8. Instalar o renovar el certificado SSL con Certbot.

## 10. Comando clave usado para SSL

El comando utilizado para generar el certificado fue similar a este:

```bash
certbot --nginx -d distribuidorajeremy.duckdns.org -d www.distribuidorajeremy.duckdns.org --agree-tos --email paredesguilder36@gmail.com --non-interactive --expand
```

## 11. Importante

El dominio fue configurado en el servidor, pero el funcionamiento final también depende de que el proveedor del dominio (DuckDNS) tenga correctamente apuntado el subdominio a la IP pública `187.127.45.61`.

En este caso, ya estaba resolviendo correctamente al servidor.
