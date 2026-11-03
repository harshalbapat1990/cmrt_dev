export function buildTransportQueryParams(datasetRevisionId: string): URLSearchParams {
  return new URLSearchParams({
    limit: '5000',
    skip: '0',
    dataset_revision_id: datasetRevisionId,
  });
}
