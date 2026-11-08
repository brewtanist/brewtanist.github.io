"""Build the existing catalogue, Shopee collections and shared visual refinement."""
import argparse
import os
from build_base import main
from marketplace import extend
from refinement import refine

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default=os.environ.get('CATALOGUE_BASE_URL') or os.environ.get('RENDER_EXTERNAL_URL'))
    args = parser.parse_args()
    if not args.base_url:
        parser.error('Set CATALOGUE_BASE_URL or use the host-provided RENDER_EXTERNAL_URL; do not guess a production URL')
    main(args.base_url)
    extend(args.base_url)
    refine(args.base_url)
