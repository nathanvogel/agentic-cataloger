import {
  Injectable,
  NotFoundException,
  InternalServerErrorException,
  Logger,
} from "@nestjs/common";
import type * as s from "zapatos/schema";
import { CategoryRepository } from "../database/repositories/category.repository";
import { ProductsRepository } from "../database/repositories/products.repository";
import { CategoryResponseDto } from "./dto/category-response.dto";
import { ProductResponseDto } from "./dto/product-response.dto";

/**
 * Service for managing categories and their products.
 * Provides business logic for category browsing and product retrieval.
 * Requirements: 1.1, 1.2, 2.1, 2.2, 8.1, 8.2, 8.5
 */
@Injectable()
export class CategoriesService {
  private readonly logger = new Logger(CategoriesService.name);

  constructor(
    private readonly categoryRepository: CategoryRepository,
    private readonly productsRepository: ProductsRepository,
  ) {}

  /**
   * Get all categories with their metadata.
   * Returns categories ordered by product count descending.
   *
   * @returns Array of all categories
   * @throws InternalServerErrorException if database query fails
   *
   * Requirements: 1.1, 1.2, 8.1, 8.2, 8.5
   */
  async getAllCategories(): Promise<CategoryResponseDto[]> {
    try {
      this.logger.log("Fetching all categories");
      const categories = await this.categoryRepository.getAllCategories();

      return categories.map((category) => this.mapCategoryToDto(category));
    } catch (error) {
      this.logger.error("Failed to fetch categories", error);
      throw new InternalServerErrorException("Failed to fetch categories");
    }
  }

  /**
   * Get all products for a specific category.
   * Validates that the category exists before fetching products.
   *
   * @param categoryId - The category ID
   * @returns Array of products in the category
   * @throws NotFoundException if category does not exist
   * @throws InternalServerErrorException if database query fails
   *
   * Requirements: 2.1, 2.2, 8.1, 8.2, 8.5
   */
  async getCategoryProducts(categoryId: number): Promise<ProductResponseDto[]> {
    try {
      this.logger.log(`Fetching products for category ${categoryId}`);

      // Validate category exists
      const category = await this.categoryRepository.getCategory(categoryId);
      if (!category) {
        this.logger.warn(`Category with ID ${categoryId} not found`);
        throw new NotFoundException(`Category with ID ${categoryId} not found`);
      }

      // Fetch products for the category
      const products =
        await this.productsRepository.getProductsByCategory(categoryId);

      return products.map((product) => this.mapProductToDto(product));
    } catch (error) {
      if (error instanceof NotFoundException) {
        throw error;
      }
      this.logger.error(
        `Failed to fetch products for category ${categoryId}`,
        error,
      );
      throw new InternalServerErrorException(
        "Failed to fetch category products",
      );
    }
  }

  /**
   * Map database category to DTO format.
   *
   * @param category - Database category object
   * @returns CategoryResponseDto
   */
  private mapCategoryToDto(
    category: s.categories.JSONSelectable,
  ): CategoryResponseDto {
    return {
      id: category.id,
      name: category.name,
      displayName: category.display_name,
      productCount: category.product_count,
      reasoning: category.reasoning,
      confidence: category.confidence,
      schemaId: category.schema_id,
      createdAt: category.created_at ? new Date(category.created_at) : null,
      updatedAt: category.updated_at ? new Date(category.updated_at) : null,
    };
  }

  /**
   * Map database product to DTO format.
   * Maps all product fields from the database to the response DTO.
   *
   * @param product - Database product object
   * @returns ProductResponseDto
   */
  private mapProductToDto(
    product: s.products.JSONSelectable,
  ): ProductResponseDto {
    return {
      id: product.id,
      name: product.name,
      supermarket: product.supermarket,
      price: product.price,
      priceText: product.price_text,
      currency: product.currency,
      unit: product.unit,
      unitPrice: product.unit_price,
      originalQuantity: product.original_quantity,
      originalUnit: product.original_unit,
      normalizedQuantity: product.normalized_quantity,
      normalizedUnit: product.normalized_unit,
      normalizedPrice: product.normalized_price,
      isDiscounted: product.is_discounted,
      discountInfo: product.discount_info,
      imageUrl: product.image_url,
      productUrl: product.product_url,
      categories: product.categories,
      attributes:
        product.attributes && typeof product.attributes === "object"
          ? (product.attributes as Record<string, any>)
          : null,
      categoryId: product.category_id,
      categorizationConfidence: product.categorization_confidence,
      attributesExtractedAt: product.attributes_extracted_at
        ? new Date(product.attributes_extracted_at)
        : null,
      scrapedAt: product.scraped_at ? new Date(product.scraped_at) : null,
    };
  }
}
