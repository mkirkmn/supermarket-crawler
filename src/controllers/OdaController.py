from src.model.ProductItem import ProductItem
from src.controllers.SiteController import SiteController


class OdaController(SiteController):
	"""
	The SiteController for the main Oda website.
	"""

	base_url = SiteController.base_url + "https://oda.com/"
	starting_section = SiteController.starting_section + "no/"
	robots_url = base_url + "robots.txt"

	def is_product_page(self, soup):
		"""
		Checks a page for the assumed characteristics of 'product pages': those
		 which do not contain any more useful links, and contain an exhaustive
		 list of products in their category/sub-category.

		On the oda site, you know you are on a dedicated product page when the
		 full categories list is no longer showing (just one category), and
		 there are also no in-page child category links on the page.

		At the moment there are about 20 items which are not found if this guard
		 is used before reading products on a page. More investigation needed
		 as to why. Using the guard saves about 20 seconds from run time.
		"""
		# check if the full category list on the left is hidden
		# if this class exists, the category list is hidden, otherwise it's visible
		# return True
		category_list = soup.find('li', {'class': 'product-category parent-category visible-xs-block'})
		print('category list')
		print(category_list)
		if not category_list:
			return False

		# now if there is a top nav bar, one of the pills must be active
		# top_nav_bar = soup.find('ul', {'class': 'nav nav-pills'})

		# print('top nav bar')
		# print(top_nav_bar.find_all('a'))
		# if not top_nav_bar.find_all('a'):
		# 	return True

		# if top_nav_bar.find('li', {'class': 'active'}):
		# 	return True
		# if there are child category headings, it also isn't a product page
		child_categories = soup.find_all('h4', {'class': 'child-category-headline'})
		if child_categories:
			return False
		return True

	def find_next_navigable_links(self, soup, cur_url, urls_to_ignore: set[str]) -> list[str]:
		"""
		Finds all links on the page which will take the crawler further towards
		 an unread product page.
		Checks for left, top, and in-page category/sub-category links, and adds
		 any which are not marked to ignore to a list.
		Returns the list of unignored links.
		"""
		next_links: list[str] = []
		# if there is a next product page button, then always add it
		next_page = soup.find('a', {'title': 'Neste side'})
		if next_page:
			# needs to use the current url because the link is just a param
			next_links.append(cur_url + next_page.get('href'))

		# # if there is a top nav bar, and one of them hasn't been clicked, click it
		# top_nav_bar_a = soup.find('ul', {'class': 'nav nav-pills'}).find_all('a')

		# if top_nav_bar_a:
		# 	nav_pill_links = [pill.get('href') for pill in top_nav_bar_a]
		# 	# find an unvisited nav pill if one exists
		# 	next_links += self._find_unvisited_urls(nav_pill_links, urls_to_ignore)

		# if there are any in-page child category links, add them
		child_categories = soup.find_all('h4', {'class': 'child-category-headline'})
		# find all the links under the headlines (ignore headlines without links)
		child_as = []
		for child in child_categories:
			child_a = child.find('a')
			if child_a:
				child_as.append(child_a)

		if child_categories:
			print(child_categories)
			child_links = [child.get('href') for child in child_as]
			# find an unvisited in-page category if one exists
			next_links += self._find_unvisited_urls(child_links, urls_to_ignore)

		# if there are any sub-categories on the category nav bar, add them
		sub_categories = soup.find_all('li', {'class': 'child-category'})
		if sub_categories:
			sub_links = [sub.find('a').get('href') for sub in sub_categories]
			# find an unvisited sub-category if one exists
			next_links +=  self._find_unvisited_urls(sub_links, urls_to_ignore)

		# if there are no more sub-categories, add the next categories
		# TODO: Is this necessary? These have aggfilterheadline too
		categories = soup.find_all('li', {'class': 'product-category parent-category'})
		if categories:
			cat_links = [cat.find('a').get('href') for cat in categories]
			# find an unvisited category if one exists
			next_links += self._find_unvisited_urls(cat_links, urls_to_ignore)

		# also add the special parent categories
		par_categories = soup.find_all('h4', {'class': 'aggregation-filter-headline'})
		# find all the links under the headlines (ignore headlines without links)
		par_as = []
		for par in par_categories:
			par_a = par.find('a')
			if par_a:
				par_as.append(par_a)

		# TODO: Do we need a guard here?
		if par_categories:
			print(par_as)
			par_links = [par.get('href') for par in par_as]
			# find an unvisited parent category if one exists
			next_links += self._find_unvisited_urls(par_links, urls_to_ignore)

		return next_links

	def get_all_product_items_in_page(self, soup):
		items = soup.findAll('div', {'class': 'product-list-item'})

		oda_items = []
		for item in items:
			oda_items.append(self._create_product_item_from_soup(item))
		return oda_items

	def _create_product_item_from_soup(self, soup):
		name = soup.find('div', {'class': 'name-main wrap-two-lines'})
		# TBD: do we want price for item or by amount?
		price = soup.find('p', {'class': 'price label label-price'})
		# discounted prices have a different class
		# TBD: should we store discounted price or normal?
		alt_price = soup.find('p', {'class': 'price label label-price-discounted'})
		details = soup.find('div', {'class': 'name-extra wrap-one-line'})
		url = soup.find('a', {'class': 'modal-link'})

		# check that each piece of metadata was found before continuing
		#  a missing name is an error, but the rest can be None
		assert name.string, "Found a product which does not have a name - this is not supported behaviour. Please investigate."
		name = name.string.strip()
		if price and price.string:
			price = price.string.strip()
		elif alt_price:
			alt_price.find('span').decompose()
			price = next(alt_price.stripped_strings)
		if details:
			details = details.get_text().strip().replace('\n', ' ')
		if url:
			url = self.base_url.strip('/') + url.get('href')

		return ProductItem(name, price, details, url)