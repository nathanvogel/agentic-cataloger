import { NestFactory } from "@nestjs/core";
import { AppModule } from "./app.module";

async function bootstrap() {
  console.log("Bootstrapping 3...");
  const app = await NestFactory.create(AppModule);
  await app.listen(process.env.PORT ?? 3010);
}
void bootstrap();
