FROM odoo:16.0@sha256:0f36a5002a200bb1649771c2cb9403ca5392d7ac4bb23f9ad500b339df3f5a3a
USER root
# Match production tzdata names, including Europe/Kyiv used by restored users.
RUN python3 -m pip install --no-cache-dir pytz==2022.7.1
USER odoo
