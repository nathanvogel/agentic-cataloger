import { Module, Global } from "@nestjs/common";
import { Pool } from "pg";
import {
  ProductsRepository,
  CategoryRepository,
  SchemaRepository,
  AgentExecutionRepository,
} from "./repositories";
import { DATABASE_POOL } from "./database.constants";

@Global()
@Module({
  providers: [
    {
      provide: DATABASE_POOL,
      useFactory: () => {
        const pool = new Pool({
          connectionString: process.env.DATABASE_URL,
        });
        return pool;
      },
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
