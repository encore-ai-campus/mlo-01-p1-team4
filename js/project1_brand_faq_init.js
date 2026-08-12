// 사용할 데이터베이스를 project1로 변경합니다.
const project1Db = db.getSiblingDB("project1");

// brand_faq 컬렉션이 없을 때만 빈 컬렉션을 생성합니다.
if (!project1Db.getCollectionNames().includes("brand_faq")) {
  project1Db.createCollection("brand_faq");
}

// source_id와 faq_id 조합에 중복을 허용하지 않는 고유 인덱스를 생성합니다.
project1Db.brand_faq.createIndex(
  { source_id: 1, faq_id: 1 },
  { unique: true }
);

// 브랜드와 카테고리 검색을 위한 인덱스를 생성합니다.
project1Db.brand_faq.createIndex(
  { brand_en: 1, brand: 1, category: 1 }
);
