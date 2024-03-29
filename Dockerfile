FROM python:3.12-slim as base

WORKDIR /usr/src/app

FROM base as build

ENV POETRY_VERSION=1.5.1

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends curl build-essential gcc libpq-dev git gpg libffi-dev \
    && mkdir -p /etc/apt/keyrings; \
     curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg; \
     echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_16.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list; \
    apt-get update && apt-get install -y -t nodistro nodejs --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
    && apt-get clean

RUN pip install "poetry==$POETRY_VERSION"

RUN python -m venv /usr/src/app/venv

COPY . .

RUN poetry export --without-hashes -f requirements.txt | /usr/src/app/venv/bin/pip install -r /dev/stdin

RUN git clone https://github.com/grundleborg/crispy-tailwind.git && cd crispy-tailwind && git checkout carshare && mv crispy_tailwind ../crispy_tailwind && cd .. && rm -rf crispy-tailwind

RUN sed -i "s/CSS_CACHE_BUSTER_VERSION/$(git rev-parse HEAD)/g" /usr/src/app/theme/templates/base.html

RUN SECRET_KEY=nothing /usr/src/app/venv/bin/python manage.py tailwind install --no-input;
RUN SECRET_KEY=nothing /usr/src/app/venv/bin/python manage.py tailwind build --no-input;
RUN SECRET_KEY=nothing /usr/src/app/venv/bin/python manage.py collectstatic --no-input;

# Clean Up
RUN rm -rf theme/static_src

FROM base as final

EXPOSE 8000

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends libpq5 && \
    apt-get clean

ENV PATH="/usr/src/app/venv/bin:$PATH"

COPY --from=build /usr/src/app /usr/src/app

RUN mkdir static_root
VOLUME /usr/src/app/static_root

CMD [ "/bin/bash", "entrypoint.sh", "app"]
