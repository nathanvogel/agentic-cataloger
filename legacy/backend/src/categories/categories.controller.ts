import {
  Controller,
  Get,
  Param,
  ParseIntPipe,
  HttpStatus,
} from "@nestjs/common";
import { ApiTags, ApiOperation, ApiResponse, ApiParam } from "@nestjs/swagger";
import { CategoriesService } from "./categories.service";
import { CategoryResponseDto } from "./dto/category-response.dto";
import { ProductResponseDto } from "./dto/product-response.dto";

/**
 * Controller for category browsing endpoints.
 * Provides REST API for retrieving categories and their products.
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5
 */
@ApiTags("categories")
@Controller("api/categories")
export class CategoriesController {
  constructor(private readonly categoriesService: CategoriesService) {}

  /**
   * Get all categories with their metadata.
   * Returns categories ordered by product count descending.
   *
   * @returns Array of all categories
   *
   * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
   */
  @Get()
  @ApiOperation({
    summary: "Get all categories",
    description:
      "Retrieve all product categories with metadata including product counts, confidence scores, and reasoning. Categories are ordered by product count in descending order.",
  })
  @ApiResponse({
    status: HttpStatus.OK,
    description: "Successfully retrieved all categories",
    type: [CategoryResponseDto],
  })
  @ApiResponse({
    status: HttpStatus.INTERNAL_SERVER_ERROR,
    description: "Failed to fetch categories from database",
  })
  async getAllCategories(): Promise<CategoryResponseDto[]> {
    return this.categoriesService.getAllCategories();
  }

  /**
   * Get all products for a specific category.
   *
   * @param id - The category ID
   * @returns Array of products in the category
   *
   * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
   */
  @Get(":id/products")
  @ApiOperation({
    summary: "Get products for a category",
    description:
      "Retrieve all products assigned to a specific category. Products are ordered alphabetically by name. Returns 404 if the category does not exist.",
  })
  @ApiParam({
    name: "id",
    type: "number",
    description: "The category ID",
    example: 1,
  })
  @ApiResponse({
    status: HttpStatus.OK,
    description: "Successfully retrieved products for the category",
    type: [ProductResponseDto],
  })
  @ApiResponse({
    status: HttpStatus.NOT_FOUND,
    description: "Category with the specified ID not found",
  })
  @ApiResponse({
    status: HttpStatus.BAD_REQUEST,
    description: "Invalid category ID format",
  })
  @ApiResponse({
    status: HttpStatus.INTERNAL_SERVER_ERROR,
    description: "Failed to fetch products from database",
  })
  async getCategoryProducts(
    @Param("id", ParseIntPipe) id: number,
  ): Promise<ProductResponseDto[]> {
    return this.categoriesService.getCategoryProducts(id);
  }
}
