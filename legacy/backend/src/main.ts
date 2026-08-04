import { NestFactory } from "@nestjs/core";
import { ValidationPipe } from "@nestjs/common";
import { SwaggerModule, DocumentBuilder } from "@nestjs/swagger";
import { AppModule } from "./app.module";

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Enable validation pipes globally
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      transform: true,
    }),
  );

  // Configure Swagger/OpenAPI
  const config = new DocumentBuilder()
    .setTitle("Price Comparison API")
    .setDescription("API for browsing product categories and products")
    .setVersion("1.0")
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup("api/docs", app, document);

  // Enable CORS
  app.enableCors({
    origin: process.env.FRONTEND_URL || "http://localhost:3011",
    credentials: true,
  });

  await app.listen(process.env.PORT ?? 3010);
  console.log(
    `Application is running on: http://localhost:${process.env.PORT ?? 3010}`,
  );
}
void bootstrap();
