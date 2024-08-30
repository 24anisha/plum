var assert = require('assert');
// import {add,subtract,multiply,stringLowerUpper,firstletter,shoes,getBook} from "../functions"
// var functionBank = require('../functions');
// require('../functions.js')();
const 
    {add, 
    subtract, 
    multiply, 
    firstletter, 
    stringLowerUpper, 
    getBook, 
    shoes} = require('../functions.js')
// TODO make tests for each of the functions I wrote 
describe('arrow', () => {
    it('simple arrow', () => {
        assert.equal(add(2, 2), 4)
        assert.equal(add(50, 39), 89)
        })
    it('complex arrow', () => {
        assert.equal(stringLowerUpper("HeLlO"),  "hello")
        assert.equal(stringLowerUpper("and goodBYE"), "AND GOODBYE")
    })
})

describe('statement', () => {
    it('simple statement', () => {
        assert.equal(subtract(2, 2), 0)
        assert.equal(subtract(50, 39), 11)
        })
    it('complex statement', () => {
        assert.equal(getBook(), true)
    })
})

describe('expression', () => {
    it('simple expression', () => {
        assert.equal(multiply(2, 5), 10)
        assert.equal(multiply(0, 11), 0)
        })
    it('complex expression', () => {
        assert.equal(firstletter("hello"), "h")
    })
})

describe('constructor', () => {
    it('new pair 1', () => {
        let newPair = new shoes(6.5, 'adidas')
        assert.equal(newPair.size, 6.5)
        assert.equal(newPair.mark, 'adidas')
        })
})




