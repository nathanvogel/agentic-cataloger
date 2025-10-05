import { Controller, Get, Query } from '@nestjs/common';
import { ProductsService } from './products.service';

@Controller('products')
export class ProductsController {
  constructor(private readonly productsService: ProductsService) {}

  @Get('search')
  async search(
    @Query('q') query: string,
    @Query('bio') bio?: string,
    @Query('supermarket') supermarket?: string,
  ) {
    return this.productsService.search(query, {
      bio: bio === 'true',
      supermarket,
    });
  }

  @Get('cheapest')
  async getCheapest(
    @Query('name') name: string,
    @Query('bio') bio?: string,
  ) {
    return this.productsService.getCheapest(name, {
      bio: bio === 'true',
    });
  }

  @Get('compare-category')
  async compareByCategory(@Query('category') category: string) {
    return this.productsService.compareByCategory(category);
  }
}
