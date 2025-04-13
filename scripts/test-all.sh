# Dans scripts/test-all.sh
#!/bin/bash
echo "Running tests for all services..."
docker-compose run django-api python manage.py test
docker-compose run FastApi pytest
docker-compose run go-api go test ./...