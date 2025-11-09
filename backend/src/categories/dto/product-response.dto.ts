import { ApiProperty } from "@nestjs/swagger";

export class ProductResponseDto {
  @ApiProperty({ description: "Product ID", example: 101 })
  id: number;

  @ApiProperty({ description: "Product name", example: "Bio Zitronen" })
  name: string;

  @ApiProperty({ description: "Supermarket name", example: "coop" })
  supermarket: string;

  @ApiProperty({
    type: Number,
    description: "Price in CHF",
    example: 2.95,
    nullable: true,
  })
  price: number | null;

  @ApiProperty({
    type: String,
    description: "Price text from source",
    example: "CHF 2.95",
    nullable: true,
  })
  priceText: string | null;

  @ApiProperty({
    type: String,
    description: "Currency code",
    example: "CHF",
    nullable: true,
  })
  currency: string | null;

  @ApiProperty({
    type: String,
    description: 'Unit (e.g., "500g", "1L")',
    example: "500g",
    nullable: true,
  })
  unit: string | null;

  @ApiProperty({
    type: String,
    description: "Unit price text",
    example: "CHF 5.90/kg",
    nullable: true,
  })
  unitPrice: string | null;

  @ApiProperty({
    type: Number,
    description: "Original quantity from source",
    example: 500,
    nullable: true,
  })
  originalQuantity: number | null;

  @ApiProperty({
    type: String,
    description: "Original unit from source",
    example: "g",
    nullable: true,
  })
  originalUnit: string | null;

  @ApiProperty({
    type: Number,
    description: "Normalized quantity",
    example: 500,
    nullable: true,
  })
  normalizedQuantity: number | null;

  @ApiProperty({
    type: String,
    description: "Normalized unit",
    example: "g",
    nullable: true,
  })
  normalizedUnit: string | null;

  @ApiProperty({
    type: Number,
    description: "Normalized price per unit",
    example: 5.9,
    nullable: true,
  })
  normalizedPrice: number | null;

  @ApiProperty({
    type: Boolean,
    description: "Has discount flag",
    example: false,
    nullable: true,
  })
  isDiscounted: boolean | null;

  @ApiProperty({
    type: String,
    description: "Discount information",
    example: "20% off",
    nullable: true,
  })
  discountInfo: string | null;

  @ApiProperty({
    type: String,
    description: "Product image URL",
    example: "https://example.com/image.jpg",
    nullable: true,
  })
  imageUrl: string | null;

  @ApiProperty({
    type: String,
    description: "Product page URL",
    example: "https://example.com/product",
    nullable: true,
  })
  productUrl: string | null;

  @ApiProperty({
    description: "Original categories from CSV",
    type: [String],
    example: ["Früchte", "Bio"],
    nullable: true,
  })
  categories: string[] | null;

  @ApiProperty({
    description: "Extracted attributes (JSONB)",
    example: { organic: true, variety: "eureka" },
    nullable: true,
  })
  attributes: Record<string, any> | null;

  @ApiProperty({
    type: Number,
    description: "Assigned category ID",
    example: 1,
    nullable: true,
  })
  categoryId: number | null;

  @ApiProperty({
    type: Number,
    description: "Categorization confidence (0-1)",
    example: 0.95,
    nullable: true,
  })
  categorizationConfidence: number | null;

  @ApiProperty({
    type: Date,
    description: "Attributes extraction timestamp",
    example: "2025-11-08T11:00:00Z",
    nullable: true,
  })
  attributesExtractedAt: Date | null;

  @ApiProperty({
    type: Date,
    description: "Scraping timestamp",
    example: "2025-11-08T09:00:00Z",
    nullable: true,
  })
  scrapedAt: Date | null;
}
