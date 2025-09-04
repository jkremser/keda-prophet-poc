ARG GIT_COMMIT="main"
ARG VERSION="main"

FROM --platform=$TARGETARCH cgr.dev/chainguard/python:latest-dev AS dev
WORKDIR /app
RUN python -m venv venv
RUN touch /app/empty
ENV PATH="/app/venv/bin":$PATH
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt


FROM --platform=$TARGETARCH cgr.dev/chainguard/python:latest
ARG GIT_COMMIT
ARG VERSION
COPY --chown=nonroot:nonroot app /app/app
COPY --chown=nonroot:nonroot data/sample-db.sqlite /app/data/
COPY --from=dev /app/venv /app/venv
COPY model /app/model
ENV PATH="/app/venv/bin:$PATH" \
    UVICORN_PORT="8000" \
    MODELS_PATH="/app/model" \
    DB_FILE="/app/data/db.sqlite" \
    GIT_COMMIT=${GIT_COMMIT} \
    VERSION=${GIT_COMMIT}
COPY --from=dev /app/empty $DB_FILE
WORKDIR /app
USER nonroot:nonroot
EXPOSE 8000/tcp
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
