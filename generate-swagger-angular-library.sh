set -euxo pipefail

#docker run -v `pwd`:/input -v `pwd`/scanner-frontend/src/lib/scanner/:/output swaggerapi/swagger-codegen-cli-v3:3.0.19 generate --additional-properties ngVersion=9.0.7 --additional-properties modelPropertyNaming=original -i /input/roboscan-swagger.json -o /output/ --lang typescript-angular
docker run -v `pwd`:/input -v `pwd`/scanner-frontend/src/lib/scanner/:/output openapitools/openapi-generator-cli generate --additional-properties ngVersion=9.0.7 --additional-properties modelPropertyNaming=original -i /input/roboscan-swagger.json -o /output/ --generator-name typescript-angular
