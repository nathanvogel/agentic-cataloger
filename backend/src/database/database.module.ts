import { Module, Global } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { Pool } from "pg";
import {
  ProductsRepository,
  CategoryRepository,
  SchemaRepository,
  AgentExecutionRepository,
} from "./repositories";

export const DATABASE_POOL = "DATABASE_POOL";

@Global()
@Module({
  providers: [
    {
      provide: DATABASE_POOL,
      useFactory: (configService: ConfigService) => {
        const pool = new Pool({
          connectionString: configService.get<string>("DATABASE_URL"),
        });
        return pool;
      },
      inject: [ConfigService],
    },
    ProductsRepository,
    CategoryRepository,
    SchemaRepository,
    AgentExecutionRepository,
  ],
  exports: [
    DATABASE_POOL,
    ProductsRepository,
    CategoryRepository,
    SchemaRepository,
    AgentExecutionRepository,
  ],
})
export class DatabaseModule {}
