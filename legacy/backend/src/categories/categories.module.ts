import { Module } from "@nestjs/common";
import { DatabaseModule } from "../database/database.module";
import { CategoriesController } from "./categories.controller";
import { CategoriesService } from "./categories.service";

/**
 * Module for category browsing functionality.
 * Provides REST API endpoints for retrieving categories and their products.
 *
 * Requirements: 1.1, 2.1
 */
@Module({
  imports: [DatabaseModule],
  controllers: [CategoriesController],
  providers: [CategoriesService],
  exports: [CategoriesService],
})
export class CategoriesModule {}
