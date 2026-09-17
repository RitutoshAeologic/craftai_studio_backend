-- ====================================================================
-- CRAFTAI STUDIO — STORAGE RLS POLICIES FOR USER REFERENCE UPLOADS
-- Allows public/anon uploads to the 'reference-images' bucket
-- ====================================================================

-- 1. Ensure RLS is active on storage.objects
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- 2. Allow public/anon inserts into 'reference-images' bucket
DROP POLICY IF EXISTS "Allow public uploads to reference-images" ON storage.objects;
CREATE POLICY "Allow public uploads to reference-images"
ON storage.objects FOR INSERT
TO public
WITH CHECK (bucket_id = 'reference-images');

-- 3. Allow public/anon updates into 'reference-images' bucket
DROP POLICY IF EXISTS "Allow public updates to reference-images" ON storage.objects;
CREATE POLICY "Allow public updates to reference-images"
ON storage.objects FOR UPDATE
TO public
USING (bucket_id = 'reference-images');

-- 4. Allow public reads from 'reference-images' bucket
DROP POLICY IF EXISTS "Allow public reads from reference-images" ON storage.objects;
CREATE POLICY "Allow public reads from reference-images"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'reference-images');
