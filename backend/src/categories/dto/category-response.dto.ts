import { ApiProperty } from "@nestjs/swagger";

export class CategoryResponseDto {
  @ApiProperty({ description: "Category ID", example: 1 })
  id: number;

  @ApiProperty({
    description: "Internal category name (kebab-case)",
    example: "lemon",
  })
  name: string;

  @ApiProperty({ description: "Display name for UI", example: "Lemon" })
  displayName: string;

  @ApiProperty({
    description: "Number of products in category",
    example: 45,
    nullable: true,
  })
  productCount: number | null;

  @ApiProperty({
    description: "LLM reasoning for category",
    example: "Products that are lemons based on consumer substitutability",
    nullable: true,
  })
  reasoning: string | null;

  @ApiProperty({
    description: "Confidence score (0-1)",
    example: 0.95,
    nullable: true,
  })
  confidence: number | null;

  @ApiProperty({
    description: "Linked schema ID",
    example: 3,
    nullable: true,
  })
  schemaId: number | null;

  @ApiProperty({
    description: "Creation timestamp",
    example: "2025-11-08T10:00:00Z",
    nullable: true,
  })
  createdAt: Date | null;

  @ApiProperty({
    description: "Last update timestamp",
    example: "2025-11-08T10:00:00Z",
    nullable: true,
  })
  updatedAt: Date | null;
}
